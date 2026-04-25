import json
from pathlib import Path
from typing import Any

import anthropic

_client: anthropic.Anthropic | None = None
_mapping_text: str = ""


def _load_mapping() -> str:
    mapping_path = Path(__file__).parent.parent / "data" / "mapped-ingredients.txt"
    return mapping_path.read_text(encoding="utf-8")


# Load once at module init — stays in prompt cache across calls
_mapping_text = _load_mapping()

_SYSTEM_ROLE = (
    "You are an expert cosmetic chemist specializing in hair colour formulations. "
    "Analyze ingredient lists and return structured JSON only."
)

_USER_TEMPLATE = """\
Product: {name}
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

_ERROR_RESULT = {
    "in_scope": False,
    "scope_reason": "",
    "components": {},
    "dye_actives": [],
    "internal_names": {},
}


def _get_client() -> anthropic.Anthropic:
    """Create the SDK client lazily to avoid import-time failures."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _parse_response_text(text: str) -> dict:
    """Strip optional markdown fences then parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    return json.loads(text)


def _normalize_result(payload: dict[str, Any]) -> dict:
    """Guarantee classifier output matches the expected schema shape."""
    return {
        "in_scope": bool(payload.get("in_scope", False)),
        "scope_reason": str(payload.get("scope_reason", "")),
        "components": payload.get("components")
        if isinstance(payload.get("components"), dict)
        else {},
        "dye_actives": payload.get("dye_actives")
        if isinstance(payload.get("dye_actives"), list)
        else [],
        "internal_names": payload.get("internal_names")
        if isinstance(payload.get("internal_names"), dict)
        else {},
    }


async def classify(name: str, url: str, ingredients_raw: str) -> dict:
    """
    Returns: {
        "in_scope": bool,
        "scope_reason": str,
        "components": {"COMPONENT NAME": ["ingredient1", ...]},
        "dye_actives": ["ingredient1", ...],
        "internal_names": {"ingredient_name": "internal_name", ...}
    }
    Never raises — returns in_scope=False with error scope_reason on failure.
    """
    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_ROLE,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": f"Ingredient mapping reference:\n\n{_mapping_text}",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": _USER_TEMPLATE.format(
                        name=name, url=url, ingredients_raw=ingredients_raw
                    ),
                }
            ],
        )
        return _normalize_result(_parse_response_text(response.content[0].text))
    except Exception as e:
        result = dict(_ERROR_RESULT)
        result["scope_reason"] = f"Classification error: {e}"
        return result
