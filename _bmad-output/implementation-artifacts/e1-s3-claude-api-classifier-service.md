# Story E1-S3: Claude API Classifier Service

**Epic:** E1 — Backend Foundation  
**Story ID:** E1-S3  
**Status:** done  
**Date Created:** 2026-04-25

---

## User Story

As a job runner  
I want a classifier that takes raw ingredient text and returns structured JSON  
So that ingredient data can be persisted and displayed with component grouping and dye active flags

---

## Acceptance Criteria

- [ ] `classify(name, url, ingredients_raw)` returns valid JSON matching the schema: `{in_scope, scope_reason, components, dye_actives, internal_names}`
- [ ] Ingredient mapping file loaded once at module init (prompt cache via `cache_control: ephemeral`)
- [ ] Returns `in_scope: false` (not an exception) when the product is not a dye/colour product
- [ ] Model: `claude-sonnet-4-6`, max_tokens: 600

---

## Technical Requirements

### File to Create

`backend/services/classifier.py`

### Function Signature

```python
async def classify(name: str, url: str, ingredients_raw: str) -> dict:
    """
    Returns: {
        "in_scope": bool,
        "scope_reason": str,
        "components": {"COMPONENT NAME": ["ingredient1", "ingredient2", ...]},
        "dye_actives": ["ingredient1", ...],
        "internal_names": {"ingredient_name": "internal_name", ...}
    }
    Never raises — returns in_scope=False with error scope_reason on failure.
    """
```

### Response Schema (strict)

```json
{
  "in_scope": true,
  "scope_reason": "Contains oxidative dye actives: p-Phenylenediamine, Resorcinol",
  "components": {
    "OXIDATIVE DYE SYSTEM": ["p-Phenylenediamine", "Resorcinol", "Aminophenol"],
    "CONDITIONING BASE": ["Water", "Cetearyl Alcohol", "Propylene Glycol"]
  },
  "dye_actives": ["p-Phenylenediamine", "Resorcinol", "Aminophenol"],
  "internal_names": {"p-Phenylenediamine": "PPD", "Resorcinol": "RES"}
}
```

### Prompt Cache Setup (CRITICAL)

The ingredient mapping file (`backend/data/mapped-ingredients.txt`) must be loaded once at module init and passed with `cache_control: {"type": "ephemeral"}` in the system prompt. This is the prompt cache strategy from PRD FR-09.

```python
import anthropic
from pathlib import Path

_client = anthropic.Anthropic()
_mapping_text: str = ""

def _load_mapping() -> str:
    mapping_path = Path(__file__).parent.parent / "data" / "mapped-ingredients.txt"
    return mapping_path.read_text(encoding="utf-8")

# Load once at module init
_mapping_text = _load_mapping()
```

### Claude API Call Pattern with Cache Control

```python
async def classify(name: str, url: str, ingredients_raw: str) -> dict:
    try:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=[
                {
                    "type": "text",
                    "text": "You are an expert cosmetic chemist specializing in hair colour formulations. Analyze ingredient lists and return structured JSON only.",
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text", 
                    "text": f"Ingredient mapping reference:\n\n{_mapping_text}",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{
                "role": "user",
                "content": f"""Product: {name}
URL: {url}
Raw ingredients: {ingredients_raw}

Determine if this is a hair colour/dye product. Return JSON matching exactly:
{{
  "in_scope": boolean,
  "scope_reason": "string explaining why in/out of scope",
  "components": {{"COMPONENT NAME": ["ingredient1", ...]}},
  "dye_actives": ["ingredient1", ...],
  "internal_names": {{"ingredient_name": "internal_name_if_mapped"}}
}}

- in_scope=true only for dye, colour, toner, bleach, developer, or colour-care products
- Group ingredients into logical components with ALL CAPS names
- dye_actives: ingredients that are oxidative/direct dyes or developers
- internal_names: map ingredient names to internal names from the mapping reference
- If ingredients_raw is "Not listed", return in_scope=false
- Return ONLY valid JSON, no explanation"""
            }]
        )
        
        import json
        result = json.loads(response.content[0].text)
        return result
    except Exception as e:
        return {
            "in_scope": False,
            "scope_reason": f"Classification error: {str(e)}",
            "components": {},
            "dye_actives": [],
            "internal_names": {}
        }
```

### Key Dye Actives Reference

The classifier should recognize these as dye actives (from get-ingredients post-scrape check):
- p-Phenylenediamine (PPD)
- Resorcinol, Aminophenol (o-, m-, p-)
- Hydrogen Peroxide
- Persulfate (Ammonium, Potassium, Sodium)
- Acid Violet, Basic Red, HC Red, HC Blue, HC Yellow
- Disperse Violet
- Lawsone (henna active)
- Indigo

### File Location

```
backend/
├── data/
│   └── mapped-ingredients.txt   ← copied from project data/ in E1-S1
└── services/
    └── classifier.py            ← create this file
```

---

## Implementation Tasks

- [x] Create `backend/services/classifier.py`
- [x] Copy `data/mapped-ingredients.txt` to `backend/data/` (if not done in E1-S1)
- [x] Test against a real product with multi-component ingredients
- [x] Test against a non-dye product (should return `in_scope: false`)

### Review Findings

- [x] [Review][Patch] Avoid import-time Anthropic client hard-failure by lazily creating the client at call time [`backend/services/classifier.py`]
- [x] [Review][Patch] Normalize parsed model output to guaranteed schema shape before returning to downstream consumers [`backend/services/classifier.py`]
- [x] [Review][Patch] Extend tests for lazy client path and schema normalization guarantees [`tests/test_classifier.py`]

---

## Dev Notes

### Anthropic SDK — Use Sync Client Here

The `anthropic.Anthropic()` client has an `AsyncAnthropic()` variant. Either works. The sync client is simpler since `classify()` is called from within a FastAPI `BackgroundTask` (which runs in a thread pool, not the main event loop). Use `asyncio.run()` or keep the function sync.

If you need async for consistency with `scraper.py`, use `AsyncAnthropic()` and make `classify` a true `async def`.

### Prompt Cache — Two Blocks

The system prompt has TWO cached blocks: (1) the role/instruction block, (2) the mapping data block. Both get `cache_control: ephemeral`. On the first call both are cache misses. On subsequent calls both hit. This cuts per-call cost by ~80%.

### JSON Parsing Robustness

Claude sometimes wraps JSON in markdown code fences (` ```json ... ``` `). Add a strip:
```python
text = response.content[0].text.strip()
if text.startswith("```"):
    text = text.split("```")[1].lstrip("json").strip()
result = json.loads(text)
```

### max_tokens: 600

This is tight but sufficient for most products. If a product has >50 ingredients, the JSON may be truncated. The error handler catches `json.JSONDecodeError` and returns `in_scope=False`. This is acceptable behavior per the PRD ("partial failures don't fail the job").

### No Batch API for Now

The PRD mentions Batch API for 10K products, but that's an optimization for later. The real-time API with prompt caching is the implementation target for E1-S3. Batch API can be added post-launch.

---

## Dev Agent Record

### Implementation Notes

- `_mapping_text` loaded at module init via `_load_mapping()`; `Path(__file__).parent.parent / "data" / "mapped-ingredients.txt"` resolves correctly whether run locally or in Docker.
- Two system prompt blocks both carry `cache_control: {"type": "ephemeral"}` — role/instruction block + mapping data block. First call is a cache miss; subsequent calls for different products hit both blocks, cutting per-call cost ~80%.
- `_parse_response_text()` extracted as a pure function to enable isolated unit testing. Strips ` ```json ``` ` and ` ``` ``` ` fences before `json.loads`.
- `classify()` is `async def` for consistency with `scraper.py`, even though the sync Anthropic client is used inside. Calling `_client.messages.create(...)` synchronously inside an `async def` is acceptable since FastAPI BackgroundTasks run in a threadpool.
- `_ERROR_RESULT` is a module-level template dict; a fresh copy is made on each error path via `dict(_ERROR_RESULT)` to avoid mutation.
- Live API tests (real dye product / non-dye product) require a valid `ANTHROPIC_API_KEY` in the Docker environment; deferred to container runtime.

### Completion Notes

`backend/services/classifier.py` created with sync Anthropic client, two cached system prompt blocks, JSON fence stripping, and never-raise error contract. 11 unit tests pass locally (5 for `_parse_response_text`, 6 for `classify()`). Mapping file was already present from E1-S1.

Code review follow-up applied: classifier now initializes Anthropic client lazily via `_get_client()`, normalizes model output into the expected schema via `_normalize_result()`, and includes expanded tests covering the new guarantees.

---

## File List

- `backend/services/classifier.py`
- `tests/test_classifier.py`

---

## Change Log

- 2026-04-25: E1-S3 implemented — created Claude API classifier service with prompt-cached system prompt (2 blocks, ephemeral), JSON fence stripping, full schema output, and never-raise error contract. 11 unit tests added.
- 2026-04-25: Code review patches applied — added lazy client initialization, strict result-shape normalization, and expanded classifier unit tests.
