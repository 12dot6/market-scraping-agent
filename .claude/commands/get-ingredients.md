Scrape ingredients from hair colour and dye-adjacent product pages.

**Input — two modes:**
- `/get-ingredients <URL>` — scrape a single URL passed as the argument.
- `/get-ingredients` (no argument) — read `input.txt` from the project root; each non-blank, non-comment line is treated as one URL. Lines starting with `#` are ignored. If the file is missing or contains no valid URLs, stop and tell the user.

Collect all URLs into `url_list` before proceeding. Process all of them in the steps below.

---

Follow these steps exactly:

1. **Close any open Playwright sessions** — call `mcp__playwright__browser_close` once at the start if a session is active. Do not close between URLs — keep the browser open for the entire batch.

2. **For each URL in `url_list`**, navigate and discover products:

   a. Navigate to the URL using `mcp__playwright__browser_navigate`. If a cookie/consent dialog appears, dismiss it before proceeding.

   b. **Discover product links** — use `mcp__playwright__browser_evaluate` to collect all `<a href>` links on the page. Apply this two-level strategy:

      **Level 1 — Direct product links:** Links whose href matches any of these patterns (in order of preference):
      - Contains `/p/`
      - Contains `/products/`
      - Contains `/professional-hair-products/`
      - Contains `/product/`
      - Contains `/color/` or `/colour/` or `/hair-color/` or `/hair-colour/`
      - Any other repeating URL pattern where many links share the same sub-path structure and the URLs are leaf-level (not a category or filter page)

      Exclude links containing: `/brands/`, `/c/`, `/collections`, `/category`, `/blog`, `/about`, `/search`, `?`, `#`, or pointing to external domains.

      **Level 2 — If no direct product links found:** The page is likely a collection/lines index. Identify intermediate collection links (sub-pages on the same domain that are not products themselves), navigate to each, and collect product links using Level 1 criteria. Deduplicate across all collection pages.

   c. **Scope filter — hair colour and dye-adjacent products only:** A product is in scope if any of the following are true:
      - Its URL or title contains: `color`, `colour`, `dye`, `tint`, `toner`, `bleach`, `developer`, `lightener`, `highlight`, `balayage`, `ombre`, `grey coverage`, `gray coverage`, `color-safe`, `colour-safe`, `color protection`, `color depositing`
      - Its URL or title suggests it is a shampoo/conditioner/mask sold as part of a colour care or colour line
      - After scraping, its ingredients contain known hair-dye actives: `p-Phenylenediamine`, `Resorcinol`, `Aminophenol`, `Hydrogen Peroxide`, `Persulfate`, `Acid Violet`, `Basic Red`, `HC Red`, `HC Blue`, `HC Yellow`, `Disperse Violet`, `Lawsone`, `Indigo`

      If the input URL is already a hair-colour-specific category (e.g. `/hair-color/`, `/color/lines`), treat all discovered products as in scope and skip the filter. Deduplicate all product URLs by href.

3. **For each product URL**, scrape ingredients:
   a. Navigate to the product page.
   b. Try these extraction strategies **in order**, stopping at the first that yields text:

      **Language note:** Pages may be in any language. Recognise ingredient headings in all languages, including but not limited to: English "Ingredients", French "Ingrédients" / "Composition", German "Inhaltsstoffe" / "Zutaten", Spanish "Ingredientes" / "Composición", Italian "Ingredienti" / "Composizione", Portuguese "Ingredientes" / "Composição", Dutch "Ingrediënten" / "Samenstelling", Polish "Składniki", Japanese "成分" / "全成分", Korean "전성분" / "성분", Chinese "成分" / "配方成分", Arabic "المكونات". Apply the same logic to stop-words in the body-text search (translate the stop list to the page language as needed).

      - **Tab/accordion:** Look for a clickable element (button, tab, h3, h4, div) whose text matches an ingredient heading in any language (see above) and click it, then wait briefly for content to expand.
      - **Heading scan:** Find any heading (h1–h4, strong, label) containing an ingredient heading in any language and read the text following it until the next heading or section break.
      - **Body text search:** Search `document.body.innerText` for an ingredient keyword in any language (see above, case-insensitive). Slice ~3000 chars forward from that position. Stop at the first of: `How to use`, `Features`, `Results`, `Our active`, `Product Details`, `Ratings`, `Read More`, `Description`, `Benefits`, `Directions` (or their equivalents in the page language).
      - **INCI pattern fallback:** Scan the full body text for a block of comma-separated ALL-CAPS words (typical INCI lists). Extract the longest such block.
   c. Capture: product name from page `<title>` (strip site name suffix after " - " or " | ") or the main `h1`.
   d. **Translate if needed:** If the extracted ingredients text is not in English, translate it to English before storing. Preserve the original INCI names (they are internationally standardised and usually Latin/English already); only translate surrounding non-INCI words or labels. If the entire list is already INCI, no translation is needed.
   e. If no ingredients found after all strategies, record `"Not listed"`.

   Store each result as `{ source_url, name, url, ingredients_text, available, scope_reason }`.

4. **Derive a slug** for each source URL: hostname (strip `www.`) + a key path segment + current date (`YYYY-MM-DD`). Examples:
   - `https://www.loreal-paris.co.uk/hair-colour` → `loreal-paris-hair-colour-2026-04-17`
   - `https://www.schwarzkopf.co.uk/en-GB/products/hair-colour.html` → `schwarzkopf-hair-colour-2026-04-17`

5. **Pre-load all reference data into memory before any file writes:**
   a. Load `data/mapped-ingredients.txt` (pipe-delimited, skip header). Build a dict `mapping: { normalised_key → internal_name }` where normalised_key is the ingredient name lowercased and stripped of trailing hyphens/numbers.
   b. If `output/ingredients-master.csv` exists, read it entirely into a dict `existing: { ingredient.lower() → { ingredient, internal_name, count } }`. If it does not exist, start with an empty dict.

6. **Aggregate all output data in memory** (single pass — no file I/O in this step):
   - Group all scraped results by slug: `slug_groups: { slug → { source_urls[], product_rows[], excluded_rows[] } }`. Products from different URLs that share the same slug (same domain, same day) are combined into one group.
   - Build `run_counts: { ingredient.lower() → { ingredient, count } }` by iterating over every ingredient token across **all** in-scope products from all URLs. Use the first-seen casing as the canonical form.

7. **Write one markdown file per slug group** to `output/<slug>.md`:
   - Frontmatter: `title`, `source_urls` (list all source URLs that contributed to this slug), `scraped` (ISO 8601 date), `product_count`, `excluded_count`.
   - One `##` section per entry in `product_rows`: product name, URL, full ingredients text.
   - Summary table: product name | ingredients available (Yes / No) | in-scope reason | source URL.
   - If `excluded_rows` is non-empty, add a collapsed `## Excluded Products` section.
   - If `output/<slug>.md` already exists (same domain, same day), **append** to it: add new `##` sections after the last existing one, update `product_count`, `excluded_count`, and `source_urls` in the frontmatter to reflect combined totals, and regenerate the summary table. Do not create a new file.

8. **Write the updated CSV** to `output/ingredients-master.csv` in one shot (merge all URLs together):
   - Merge `run_counts` into `existing` entirely in memory:
     - For each entry in `run_counts`: if its lowercased key exists in `existing`, increment `count`; otherwise add a new entry.
     - Preserve `internal_name` from `existing` rows. For new rows only, resolve `internal_name` from `mapping` using this priority (stop at first match):
       1. Exact key match (case-insensitive).
       2. Scraped name contains a mapping key as a substring.
       3. Mapping key contains the scraped name as a substring.
       4. Strip trailing numbers/hyphens from both and compare.
       5. No match → leave `internal_name` empty.
     - When multiple mapping keys match, prefer the longer/more specific key.
   - Sort the merged dict values descending by `count`, then alphabetically by `ingredient` for ties.
   - Write the sorted result as CSV (`ingredient,internal_name,count`) in a single write operation.

9. **Report total elapsed time** — after all files are written, display a summary line:
   - Record the start time before step 1 begins (note the wall-clock time mentally or via a `Date.now()` call in the first `browser_evaluate`).
   - At the very end, compute elapsed time and print: `Total time: X min Y sec (HH:MM:SS start → HH:MM:SS end)`.

**Notes:**
- Never modify `data/mapped-ingredients.txt`.
- All output goes to `output/`. Never write files elsewhere.
- When processing a batch from `input.txt`, each domain produces its own dated MD file. The CSV is updated once at the end across all URLs.
- This command is designed to work on any hair/beauty product website — adapt product link detection and ingredient extraction heuristics based on what you observe on the actual page.
- **Scope:** Only hair colour, hair dye, and dye-adjacent products are scraped in full. A shampoo or conditioner qualifies if marketed for colour-treated hair or if it contains dye actives. When in doubt, scrape it and let the ingredient check decide.
