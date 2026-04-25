---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
documentSelections:
  prd:
    - prd-formulation-wiki-web-app-2026-04-24.md
  architecture:
    - architecture-formulation-wiki-web-app-2026-04-24.md
  epics:
    - epics-and-stories-formulation-wiki-web-app-2026-04-24.md
  ux: []
---

# Implementation Readiness Assessment Report

**Date:** 2026-04-24
**Project:** formulation-wiki

## Document Discovery

### PRD Files Found
- Whole: `prd-formulation-wiki-web-app-2026-04-24.md`
- Sharded: None

### Architecture Files Found
- Whole: `architecture-formulation-wiki-web-app-2026-04-24.md`
- Sharded: None

### Epics & Stories Files Found
- Whole: `epics-and-stories-formulation-wiki-web-app-2026-04-24.md`
- Sharded: None

### UX Files Found
- Whole: None
- Sharded: None

### Discovery Notes
- No duplicate whole/sharded document conflicts were found.
- UX design artifact is currently missing; readiness can proceed with reduced UX-specific validation coverage.

## PRD Analysis

### Functional Requirements

FR1: URL Input & Job Submission  
- Textarea accepting one URL per line
- File upload parsing `input.txt` format (strips `#` comments)
- Domain chip preview below textarea
- HTML5 URL validation; submit disabled until >=1 URL
- `POST /api/jobs` returns `job_id` immediately; scraping runs as BackgroundTask

FR2: Live Job Progress  
- SSE stream at `GET /api/jobs/{id}/stream`
- Progress bar (done/total, %), estimated time remaining
- Live feed: product name + in-scope/excluded status as each completes
- Stats panel: running counts for in-scope, excluded, errors, avg time/product
- "View Results" button appears on job completion

FR3: Run Results - Products Tab  
- ProductCard per scraped in-scope product
- Ingredient display: component sections (ALL CAPS headers), dye actives as amber warning pills
- Lists >8 ingredients collapsed with "Show all N" toggle
- Mapped ingredients: dotted underline + hover tooltip showing internal name
- INCI names preserved exactly as scraped

FR4: Run Results - Ingredients Tab  
- Table: ingredient name, internal name, count, frequency bar
- Dye active rows: amber left border
- Row click -> expandable panel listing containing products
- Client-side sort by count (default) or name
- Filter: dye actives only toggle
- Search box (client-side)

FR5: Run Results - Excluded Tab  
- Table: product name, URL, exclusion reason

FR6: Export  
- Per-run: CSV, MD, ZIP (CSV + MD combined)
- Global: master CSV across all runs
- Export bar always visible at top of Run Results screen

FR7: Global Ingredients Screen  
- Same ingredient table as FR4 across all runs
- Run filter dropdown
- Date range filter
- [Download Master CSV] button

FR8: Job History  
- Home screen lists recent runs: date, product count, status, [View] link
- `GET /api/jobs` returns jobs most-recent-first

FR9: Classification (Claude API)  
- Model: `claude-sonnet-4-6`
- Returns: `in_scope`, `scope_reason`, `components` (grouped ingredients), `dye_actives`, `internal_names`
- Ingredient mapping file loaded once at module startup (prompt cache)
- For 10K products: use Anthropic Batch API (50% discount)

Total FRs: 9

### Non-Functional Requirements

NFR1 (Scalability): Support 10K total products over time (not concurrently) with no high-traffic requirement.

NFR2 (Performance/Throughput): Sequential scraping target approximately 5 seconds per product; overnight job completion is acceptable.

NFR3 (Availability/Resilience): SQLite persistence must survive container restarts; WAL mode enabled.

NFR4 (Cost): Total API cost target <= $15 for 10K products by using Batch API for larger runs.

NFR5 (Deployment/Operability): Single Docker container deployment via `docker compose up -d` with app available at `http://localhost:8000`.

NFR6 (Security/Secrets): `ANTHROPIC_API_KEY` provided via `.env` rather than hardcoded values.

NFR7 (Usability): Browser-based submission and monitoring usable by non-technical users (remove CLI dependency).

NFR8 (Reliability constraints): Known limitations documented with trigger thresholds for queueing, DB migration, and scrape parallelism.

Total NFRs: 8

### Additional Requirements

- Database requirement: four-table model (`jobs`, `products`, `ingredients`, `product_ingredients`).
- API surface requirement: jobs, stream, results, and export endpoints must be provided.
- Design system requirement: Shadcn/ui with specified color palette semantics (success/danger/accent).
- Out-of-scope constraints: no multi-tenant auth, no SSR/SEO, no enterprise infrastructure stack.

### PRD Completeness Assessment

- PRD is clear and implementation-oriented with explicit FR coverage and constraints.
- NFRs are present but somewhat distributed across sections (goals, constraints, deployment, limitations) rather than a single dedicated NFR section.
- UX artifact is not included separately; UI requirements exist in PRD but detailed UX validation depth is reduced.

## Epic Coverage Validation

### Coverage Matrix

| FR Number | PRD Requirement | Epic Coverage | Status |
| --------- | --------------- | ------------- | ------ |
| FR1 | URL Input & Job Submission | E1 (API submission), E2-S2 (UI input/upload/submit) | Covered |
| FR2 | Live Job Progress | E2-S1 (SSE endpoint), E2-S3 (live progress UI) | Covered |
| FR3 | Run Results - Products Tab | E3-S1 (ProductCard), E3-S3 (Products tab) | Covered |
| FR4 | Run Results - Ingredients Tab | E3-S2 (IngredientTable), E3-S3 (Ingredients tab integration) | Covered |
| FR5 | Run Results - Excluded Tab | E2/E3 result shaping, E3-S3 Excluded tab acceptance criteria | Covered |
| FR6 | Export | E3-S4 export endpoints, E3-S3 export bar UI | Covered |
| FR7 | Global Ingredients Screen | E4-S1 (global table, filters, master CSV, chart) | Covered |
| FR8 | Job History | E1-S4 (`GET /api/jobs`), E2-S2 recent runs list | Covered |
| FR9 | Classification (Claude API) | E1-S3 classifier service and acceptance criteria | Covered |

### Missing Requirements

No missing FR coverage found. All PRD FRs (FR1-FR9) are traceable to one or more epics/stories.

### Coverage Statistics

- Total PRD FRs: 9
- FRs covered in epics: 9
- Coverage percentage: 100%

## UX Alignment Assessment

### UX Document Status

Not Found in `planning-artifacts`.

### Alignment Issues

- No standalone UX artifact is available to validate user journeys, information architecture, or interaction-level details against PRD and architecture.
- Architecture and epics do include substantial UI implementation detail, but this is not equivalent to an explicit UX spec.

### Warnings

- UX is clearly implied (browser-based, multi-screen user-facing app), so missing UX documentation is a readiness warning.
- Recommendation: create a lightweight UX artifact before implementation for flow clarity (screen map + key interactions + error/empty-state behavior).

## Epic Quality Review

### Epic FR Coverage Extracted

- FR1: Covered in E1 and E2-S2
- FR2: Covered in E2-S1 and E2-S3
- FR3: Covered in E3-S1 and E3-S3
- FR4: Covered in E3-S2 and E3-S3
- FR5: Covered in E3-S3
- FR6: Covered in E3-S4 and E3-S3
- FR7: Covered in E4-S1
- FR8: Covered in E1-S4 and E2-S2
- FR9: Covered in E1-S3

Total FRs in epics: 9

### Quality Findings by Severity

#### Critical Violations

1. Epic naming and goals are predominantly technical milestones, not user-value slices.
   - Examples: "Backend Foundation", "Job Pipeline & Live Progress", "Results UI & Export".
   - Impact: weak vertical slicing, reduced independent release value per epic.
   - Recommendation: reframe each epic to explicit user outcomes (e.g., "Submit and monitor scrape jobs end-to-end").

2. Story definitions are heavily implementation-task centric rather than independently releasable user value.
   - Examples: scaffold, router creation, service wiring, component construction as standalone stories.
   - Impact: stories risk becoming technical task bundles instead of testable value increments.
   - Recommendation: split into user-facing thin slices with technical tasks as sub-tasks.

#### Major Issues

1. Acceptance criteria are generally testable but not consistently formatted in Given/When/Then BDD style.
   - Impact: ambiguity in QA handoff and acceptance consistency.
   - Recommendation: normalize ACs to Given/When/Then format for each story.

2. Dependency structure is mostly sequential and acceptable, but explicit dependency mapping is not documented per story.
   - Impact: execution risk when parallel work begins.
   - Recommendation: add explicit "Depends on" and "Blocks" metadata at story level.

3. Database/entity creation pattern is partially front-loaded in E1 scaffold.
   - Impact: increases risk of broad upfront schema assumptions.
   - Recommendation: where practical, create/extend schema incrementally with story needs.

#### Minor Concerns

1. Minor terminology inconsistencies (`FR-xx` vs `FRx`, "Results UI" vs "Run Results").
2. Some UI behavior detail appears both in PRD and epics, creating potential dual-source drift.
3. A few tasks include implementation hints that may constrain solution flexibility prematurely.

## Summary and Recommendations

### Overall Readiness Status

NEEDS WORK

### Critical Issues Requiring Immediate Action

1. Missing standalone UX artifact for a clearly UI-driven product.
2. Epic/story framing should be converted from technical milestones to user-value slices.
3. Story acceptance criteria format should be standardized for verification rigor.

### Recommended Next Steps

1. Create a lightweight UX spec (`bmad-create-ux-design`) covering screen map, key journeys, empty/error states, and interaction contracts.
2. Refactor epic/story framing into vertical user slices while keeping existing task detail as implementation notes.
3. Normalize all story acceptance criteria to Given/When/Then and add explicit dependency metadata.
4. Re-run implementation readiness check after updates to confirm closure of critical gaps.

### Final Note

This assessment identified 8 issues across 3 categories (critical, major, minor). Address the critical issues before proceeding to implementation. These findings can be used to improve the artifacts, or you may choose to proceed as-is with acknowledged risk.
