# formulation-wiki — Setup Guide

A Claude Code project that scrapes hair colour product pages, extracts ingredient lists, and maintains a cumulative ingredient frequency database.

---

## Prerequisites

- **Node.js** (v18+) — [nodejs.org](https://nodejs.org)
- **Claude Code** — CLI and/or VSCode extension installed

Verify before continuing:
```bash
node --version
npx --version
```

---

## 1. Get the project

Clone or copy the project folder to your machine. The structure should look like this:

```
formulation-wiki/
├── .claude/
│   ├── commands/get-ingredients.md   ← the /get-ingredients slash command
│   ├── settings.json                 ← shared permissions and hooks
│   └── settings.local.json          ← your personal overrides (gitignored)
├── .gitignore
├── .mcp.json                         ← Playwright MCP config for VSCode
├── CLAUDE.md                         ← instructions Claude reads each session
├── input.txt                         ← URL list for batch scraping
├── data/
│   └── mapped-ingredients.txt        ← ingredient → internal name mapping
├── output/                           ← all scraped output goes here
│   └── archive/
└── setup_guide.md                    ← this file
```

---

## 2. Set up the Playwright MCP server

The `/get-ingredients` command uses Playwright (via MCP) to browse product pages. Setup differs slightly between the CLI and the VSCode extension.

### Claude Code CLI

Add Playwright MCP globally:
```bash
claude mcp add playwright --command "cmd /c npx @playwright/mcp@latest"
```

> **macOS / Linux:** use `--command "npx"` and `--args "@playwright/mcp@latest"` instead.

Verify it connected:
```bash
claude mcp list
# playwright: cmd /c npx @playwright/mcp@latest - ✓ Connected
```

### Claude Code VSCode Extension

The VSCode extension reads from `.mcp.json` in the project root — this file is already included in the project.

Reload the VSCode window after opening the project:

`Ctrl+Shift+P` → **Developer: Reload Window**

Playwright MCP tools will be available after the reload. The first run will download `@playwright/mcp` via npx if it is not already cached.

> **macOS / Linux:** edit `.mcp.json` and change `"command": "cmd"` / `"args": ["/c", "npx", "@playwright/mcp@latest"]` to `"command": "npx"` / `"args": ["@playwright/mcp@latest"]`.

---

## 3. Configure the ingredient mapping

`data/mapped-ingredients.txt` maps raw INCI ingredient names to your internal names. This file is **read-only** — never modify it during a scraping session.

Format (pipe-delimited, first line is a header):
```
Ingredients | Internal Name
Aqua        | House Water Base
Resorcinol  | Dye Anchor
```

Edit this file before your first run to add your own internal names. Any ingredient the scraper encounters that has no match will be recorded with a blank internal name — you can fill those in later and re-run.

---

## 4. Run a scrape

The `/get-ingredients` command supports two modes.

### Single URL

Pass a URL directly as the argument:

```
/get-ingredients https://www.loreal-paris.co.uk/hair-colour
```

### Batch mode (multiple URLs)

Add URLs to `input.txt` — one per line, lines starting with `#` are ignored:

```
# input.txt
https://www.loreal-paris.co.uk/hair-colour
https://www.schwarzkopf.co.uk/en-GB/products/hair-colour.html
https://www.wella.com/professional/en-GB/hair-products/hair-colour
```

Then run with no argument:

```
/get-ingredients
```

In both modes the command will:
1. Open the URL(s) in a single Playwright browser session (browser stays open for the whole batch)
2. Discover all in-scope hair colour / dye-adjacent product links on each page
3. Navigate to each product page and extract the ingredient list
4. Write one dated markdown file per domain to `output/` (e.g. `loreal-paris-hair-colour-2026-04-17.md`)
5. Merge all ingredients from all URLs into `output/ingredients-master.csv` in one pass

Re-running the same site on the same day appends to the existing dated file rather than creating a new one.

---

## 5. Understand the outputs

### `output/<slug>-<date>.md`

One file per site per day. Contains:
- Frontmatter: source URL, scrape date, product count
- One section per product with its full ingredient list
- A summary table: product name, ingredients available, why it was in scope
- A collapsed section for any products excluded by the scope filter

### `output/ingredients-master.csv`

Cumulative across all runs and all sites. Columns:

| Column | Description |
|--------|-------------|
| `ingredient` | Raw INCI name as found on the page |
| `internal_name` | Your mapped name from `mapped-ingredients.txt` |
| `count` | Total occurrences across all scraped products |

Sorted descending by count. Use this to track which ingredients appear most frequently across brands.

---

## 6. Automatic cleanup

A stop hook is configured in `.claude/settings.json` that deletes Playwright's temporary log and snapshot files from `.playwright-mcp/` at the end of every session. No manual cleanup needed.

---

## 7. Personalising your setup

Add any session-specific permission rules to `.claude/settings.local.json`. This file is gitignored so your entries won't affect other users. For example, to pre-approve a specific site:

```json
{
  "permissions": {
    "allow": [
      "WebFetch(domain:www.example.com)"
    ]
  }
}
```
