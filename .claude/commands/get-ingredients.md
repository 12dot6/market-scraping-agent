Scrape ingredients from hair colour and dye-adjacent product pages.

**Input — two modes:**
- `/get-ingredients <URL>` — scrape a single URL passed as the argument.
- `/get-ingredients` (no argument) — read `input.txt` from the project root; skip blank lines and lines starting with `#`. Stop if file is missing or has no valid URLs.

Collect all URLs into `url_list` before proceeding.

---

## Token efficiency rules (apply throughout)

- **Never call `mcp__playwright__browser_snapshot` or `mcp__playwright__browser_take_screenshot`** — use `mcp__playwright__browser_evaluate` with targeted JS for all data extraction.
- **Never store full ingredient text in memory across multiple products.** Discard raw text after writing; keep only tokenised ingredient names for CSV aggregation.
- **Cap products per source URL at 100.** Note the cap in the output frontmatter if hit.
- **Do not load reference data (`mapped-ingredients.txt`, `ingredients-master.csv`) until step 7**, after all scraping is complete. These files must not sit in context during browser work.
- **Combine all ingredient extraction strategies into a single `browser_evaluate` call** (see step 3b). Never make multiple probing calls to understand page structure first.

---

Follow these steps exactly:

1. **Close any open Playwright sessions** — call `mcp__playwright__browser_close` once at the start. Keep the browser open for the entire batch.

2. **For each URL in `url_list`**, navigate and discover products:

   a. Navigate with `mcp__playwright__browser_navigate`. Dismiss any cookie/consent dialog via `browser_evaluate` (find and `.click()` a button by text/aria-label matching accept/agree/close/consent).

   b. **Discover product links** via `browser_evaluate`. Two-level strategy:

      **Level 1 — Direct product links:** href contains `/p/`, `/products/`, `/professional-hair-products/`, `/product/`, `/color/`, `/colour/`, `/hair-color/`, `/hair-colour/`, or any repeating leaf-level URL pattern.
      Exclude hrefs containing: `/brands/`, `/c/`, `/collections`, `/category`, `/blog`, `/about`, `/search`, `?`, `#`, or external domains.

      **Level 2 — If no direct links found:** Navigate intermediate collection sub-pages on the same domain, collect Level-1 links from each. Deduplicate across all pages.

   c. **Scope pre-filter (URL/title only — do not load reference data):** Keep a product if its URL or title contains any of: `color`, `colour`, `dye`, `tint`, `toner`, `bleach`, `developer`, `lightener`, `highlight`, `balayage`, `ombre`, `grey coverage`, `gray coverage`, `color-safe`, `colour-safe`, `color protection`, `color depositing`, or suggests a shampoo/conditioner/mask in a colour care line.

      If the source URL is already a hair-colour category path (e.g. `/hair-color/`, `/color/lines`), treat all discovered products as in scope — skip this filter entirely.

      Products that pass URL/title filter are **tentatively in scope**. Products that fail are marked excluded immediately — do not scrape their ingredients.

      Deduplicate all product URLs by href.

3. **For each tentatively in-scope product URL**, scrape ingredients:

   a. Navigate to the product page.

   b. **Extract ingredients in a single `browser_evaluate` call** using this combined strategy — try each in order, return the first result with >30 chars:

      ```js
      () => {
        const HEADING = /ingr|compos|inhalt|ingrédients|składn|成分|전성분|ingredienti|ingredientes|المكونات/i;
        const STOP = /how to use|features|results|our active|product details|ratings|read more|description|benefits|directions/i;
        const MAX = 1500;

        // 1. Accordion/tab: find heading-matching clickable, click, read expanded body
        const btn = [...document.querySelectorAll('button,h3,h4,[role=tab],summary')]
          .find(el => HEADING.test(el.textContent) && el.textContent.trim().length < 60);
        if (btn) {
          btn.click();
          const scope = btn.closest('[class*="Accordion" i],[class*="panel" i],[class*="tab" i]') || btn.parentElement;
          const inner = scope && [...scope.querySelectorAll('[class*="body" i],[class*="content" i],[class*="inner" i]')]
            .find(el => el !== btn && el.textContent.trim().length > 30);
          const t = inner ? inner.textContent.trim().slice(0, MAX) : '';
          if (t.length > 30) return t;
        }

        // 2. Heading scan: find heading, collect nextElementSibling text
        const h = [...document.querySelectorAll('h1,h2,h3,h4,strong,label')]
          .find(el => HEADING.test(el.textContent) && el.textContent.trim().length < 60);
        if (h) {
          let text = '', el = h.nextElementSibling;
          while (el && text.length < MAX) { text += el.textContent; el = el.nextElementSibling; }
          const s = text.search(STOP);
          const result = (s > 50 ? text.slice(0, s) : text).trim().slice(0, MAX);
          if (result.length > 30) return result;
        }

        // 3. Body text search
        const body = document.body.innerText;
        const idx = body.search(HEADING);
        if (idx !== -1) {
          let chunk = body.slice(idx, idx + MAX);
          const s = chunk.search(STOP); if (s > 50) chunk = chunk.slice(0, s);
          if (chunk.trim().length > 30) return chunk.trim();
        }

        // 4. INCI fallback: longest block of comma-separated CAPS-dominant text
        const matches = body.match(/(?:[A-Z][A-Z\d\s\-\/\(\)]{5,},\s*){3,}[A-Z][A-Z\d\s\-\/\(\)]{5,}/g);
        return matches ? matches.sort((a,b) => b.length - a.length)[0].slice(0, MAX) : null;
      }
      ```

      **Language note:** The `HEADING` regex covers: English (Ingredients), French (Ingrédients/Composition), German (Inhaltsstoffe), Spanish/Portuguese (Ingredientes), Italian (Ingredienti), Polish (Składniki), Japanese/Chinese (成分), Korean (전성분), Arabic (المكونات). INCI names are internationally standardised — no translation needed for the ingredient list itself.

   c. **Post-scrape scope check:** If URL/title didn't confirm scope, check extracted ingredients for dye actives: `p-Phenylenediamine`, `Resorcinol`, `Aminophenol`, `Hydrogen Peroxide`, `Persulfate`, `Acid Violet`, `Basic Red`, `HC Red`, `HC Blue`, `HC Yellow`, `Disperse Violet`, `Lawsone`, `Indigo`. If none found, mark excluded.

   d. Capture product name from `<title>` (strip suffix after ` - ` or ` | `) or the main `h1`.

   e. If no ingredients found after all strategies, record `"Not listed"`.

   Store each result as `{ source_url, name, url, ingredients_text, available, scope_reason }`.

4. **Derive a slug** for each source URL: hostname (strip `www.`) + key path segment + date. Example: `https://www.loreal-paris.co.uk/hair-colour` → `loreal-paris-hair-colour-2026-04-17`.

5. **Write MD files** — for each source URL as soon as its products are scraped:

   Write/append `output/<slug>.md`:
   - Frontmatter: `title`, `source_urls`, `scraped` (ISO 8601), `product_count`, `excluded_count`.
   - One `##` section per in-scope product: name, URL, full ingredients text.
   - Summary table: product name | ingredients available (Yes/No) | in-scope reason | source URL.
   - If excluded products exist, add a collapsed `<details>` section listing them.
   - If the file already exists (same domain, same day), append and update frontmatter totals.

6. **Accumulate `run_counts`** across all URLs (in memory — ingredient names only, no raw text):
   - Tokenise each in-scope product's ingredients text into individual names, then discard the raw text.
   - Merge into `run_counts: { ingredient.lower() → { ingredient, count } }` using first-seen casing.

7. **Load reference data and write CSV** — after all URLs are processed:

   a. Read `data/mapped-ingredients.txt` (pipe-delimited, skip header) into `mapping: { normalised_key → internal_name }` where normalised_key is lowercased with trailing hyphens/numbers stripped.

   b. Read `output/ingredients-master.csv` if it exists into `existing: { ingredient.lower() → { ingredient, internal_name, count } }`. Otherwise start empty.

   c. Merge `run_counts` into `existing`:
      - If key exists: increment count, preserve `internal_name`.
      - If new: resolve `internal_name` from `mapping` using this priority (stop at first match): (1) exact, (2) scraped name contains mapping key, (3) mapping key contains scraped name, (4) strip trailing numbers/hyphens and compare. Prefer longer/more specific match. Leave blank if no match.

   d. Sort descending by `count`, then alphabetically by `ingredient` for ties.

   e. Write `output/ingredients-master.csv` as `ingredient,internal_name,count`.

8. **Report elapsed time:** `Total time: X min Y sec (HH:MM:SS start → HH:MM:SS end)`.

---

**Notes:**
- Never modify `data/mapped-ingredients.txt`.
- All output goes to `output/`. Never write files elsewhere.
- Adapt product link detection and extraction heuristics based on what you observe on the actual page.
- **Scope:** Only hair colour, dye, and dye-adjacent products. A shampoo/conditioner qualifies if marketed for colour-treated hair or if it contains dye actives. When in doubt, scrape and let the post-scrape check decide.
