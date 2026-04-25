from playwright.async_api import async_playwright

ONE_SHOT_JS = """
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
  const matches = body.match(/(?:[A-Z][A-Z\\d\\s\\-\\/\\(\\)]{5,},\\s*){3,}[A-Z][A-Z\\d\\s\\-\\/\\(\\)]{5,}/g);
  return matches ? matches.sort((a,b) => b.length - a.length)[0].slice(0, MAX) : null;
}
"""

_COOKIE_DISMISS_JS = """
() => {
  const dismissBtn = [...document.querySelectorAll('button')]
    .find(b => /accept|agree|close|consent|ok/i.test(b.textContent));
  if (dismissBtn) dismissBtn.click();
}
"""


def _extract_name(title: str, h1: str) -> str:
    """Strip site-name suffix from page title; fall back to h1."""
    if title:
        for sep in (" - ", " | ", " – "):
            if sep in title:
                return title.split(sep)[0].strip()
        return title.strip()
    return (h1 or "").strip()


async def scrape(url: str) -> dict:
    """
    Returns: {"url": str, "name": str, "ingredients_raw": str}
    Never raises — on any failure returns ingredients_raw="Not listed"
    """
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.set_default_timeout(30_000)
            await page.goto(url, wait_until="domcontentloaded")

            # Dismiss cookie/consent dialog
            try:
                await page.evaluate(_COOKIE_DISMISS_JS)
            except Exception:
                pass

            # Extract product name
            title = await page.title()
            h1 = ""
            try:
                h1 = await page.inner_text("h1")
            except Exception:
                pass
            name = _extract_name(title, h1)

            # Run one-shot ingredient extraction
            ingredients = None
            try:
                ingredients = await page.evaluate(ONE_SHOT_JS)
            except Exception:
                pass

            return {
                "url": url,
                "name": name,
                "ingredients_raw": (ingredients or "").strip() or "Not listed",
            }
    except Exception as e:
        return {"url": url, "name": "", "ingredients_raw": "Not listed", "error": str(e)}
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
