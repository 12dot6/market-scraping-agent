# formulation-wiki

You are an ingredient research assistant. Read this file at the start of every session.

## Directory Structure

```
formulation-wiki/
├── CLAUDE.md                       ← this file
├── input.txt                       ← list of URLs for batch scraping (one per line)
├── data/
│   └── mapped-ingredients.txt      ← ingredient → internal name mapping (read-only)
├── .claude/
│   └── commands/
│       └── get-ingredients.md      ← /get-ingredients slash command
└── output/                         ← all scraped output files go here
```

## Conventions

- Dates: ISO 8601 — `YYYY-MM-DD`.
- File names: lowercase, hyphen-separated — e.g. `sitename-hair-color-YYYY-MM-DD.md`.
- All output goes to `output/`. Never write files elsewhere.
- Never modify files in `data/`.
