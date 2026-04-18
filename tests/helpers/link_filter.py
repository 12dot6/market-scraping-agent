"""
Reference implementation of the product link detection logic (step 2b of get-ingredients.md).

A link is a direct product link if its href:
  - Contains a product-path pattern (/p/, /products/, /product/, /colour/, /color/, etc.)
  - Does NOT contain an excluded path segment (/brands/, /c/, /collections, /category,
    /blog, /about, /search)
  - Does NOT contain ? or # query/fragment markers
  - Points to the same domain (not an external URL)

Returns one of: "product", "collection", "excluded"
"""

import re
from urllib.parse import urlparse

PRODUCT_PATTERNS = [
    r"/p/",
    r"/products/",
    r"/professional-hair-products/",
    r"/product/",
    r"/colou?r/",
    r"/hair-colou?r/",
]

EXCLUDED_SEGMENTS = [
    "/brands/", "/c/", "/collections", "/category",
    "/blog", "/about", "/search",
]


def classify_link(href: str, base_domain: str) -> str:
    """
    Classify a link href as 'product', 'collection', or 'excluded'.

    Args:
        href: The href value of the anchor tag (absolute or relative).
        base_domain: The hostname of the source page (e.g. 'www.example.com').

    Returns:
        'product'    — matches a product URL pattern
        'collection' — on-domain page that might be a sub-collection
        'excluded'   — should be ignored
    """
    if not href:
        return "excluded"

    # Fragment-only or javascript links
    if href.startswith("#") or href.startswith("javascript:"):
        return "excluded"

    # External domain check (only applies to absolute URLs)
    if href.startswith("http"):
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != base_domain:
            return "excluded"
        path = parsed.path
        query = parsed.query
    else:
        path = href.split("?")[0]
        query = href.split("?")[1] if "?" in href else ""

    # Query string → excluded
    if query:
        return "excluded"

    # Fragment in path → excluded
    if "#" in path:
        return "excluded"

    # Excluded segment check
    for segment in EXCLUDED_SEGMENTS:
        if segment in path:
            return "excluded"

    # Product pattern check
    for pattern in PRODUCT_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return "product"

    return "collection"
