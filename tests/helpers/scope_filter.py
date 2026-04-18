"""
Reference implementation of the product scope filter (step 2c of get-ingredients.md).

A product is in scope if:
  1. Its URL or title contains a scope keyword, OR
  2. Its scraped ingredients contain a known hair-dye active.

If the source collection URL already indicates a hair-colour category
(contains /hair-color/, /colour/, /color/ etc.), all products are in scope
and the filter should be skipped entirely — pass skip_filter=True.
"""

SCOPE_KEYWORDS = frozenset([
    "color", "colour", "dye", "tint", "toner", "bleach", "developer",
    "lightener", "highlight", "balayage", "ombre", "grey coverage",
    "gray coverage", "color-safe", "colour-safe", "color protection",
    "color depositing",
])

DYE_ACTIVES = frozenset([
    "p-phenylenediamine", "resorcinol", "aminophenol", "hydrogen peroxide",
    "persulfate", "acid violet", "basic red", "hc red", "hc blue", "hc yellow",
    "disperse violet", "lawsone", "indigo",
])

CATEGORY_URL_PATTERNS = [
    "/hair-color/", "/hair-colour/", "/color/", "/colour/",
]


def source_url_is_colour_category(url: str) -> bool:
    """True if the source collection URL is already a hair-colour category."""
    lower = url.lower()
    return any(pat in lower for pat in CATEGORY_URL_PATTERNS)


def in_scope_by_url_or_title(url: str, title: str) -> bool:
    """True if the product URL or title contains a scope keyword."""
    text = (url + " " + title).lower()
    return any(kw in text for kw in SCOPE_KEYWORDS)


def in_scope_by_ingredients(ingredients_text: str) -> bool:
    """True if the ingredient list contains a known hair-dye active."""
    lower = ingredients_text.lower()
    return any(active in lower for active in DYE_ACTIVES)


def is_in_scope(
    url: str,
    title: str,
    ingredients_text: str,
    skip_filter: bool = False,
) -> tuple[bool, str]:
    """
    Determine if a product is in scope.

    Returns:
        (in_scope: bool, reason: str)
        reason is one of: 'category', 'URL match', 'title match',
                          'ingredient match', 'out of scope'
    """
    if skip_filter:
        return True, "category"

    if in_scope_by_url_or_title(url, ""):
        return True, "URL match"

    if in_scope_by_url_or_title("", title):
        return True, "title match"

    if ingredients_text and in_scope_by_ingredients(ingredients_text):
        return True, "ingredient match"

    return False, "out of scope"
