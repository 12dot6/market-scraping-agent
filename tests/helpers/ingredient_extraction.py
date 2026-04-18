"""
Reference implementation of the ingredient extraction helpers (step 3b–3d of get-ingredients.md).

Covers:
  - Multilingual ingredient heading detection (step 3b)
  - INCI name identification (step 3d — preserved during translation)
  - Language detection heuristic (step 3d — triggers translation when non-English)
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Multilingual ingredient headings
# ---------------------------------------------------------------------------

# Each entry is a set of normalised lowercase strings (accents stripped) that
# the agent should recognise as an ingredient heading in any supported language.
INGREDIENT_HEADINGS: dict[str, list[str]] = {
    "en": ["ingredients", "ingredient list", "full ingredient list", "inci"],
    "fr": ["ingredients", "ingrédients", "composition"],
    "de": ["inhaltsstoffe", "zutaten", "zusammensetzung"],
    "es": ["ingredientes", "composición", "composicion", "lista de ingredientes"],
    "it": ["ingredienti", "composizione", "lista ingredienti"],
    "pt": ["ingredientes", "composição", "composicao", "lista de ingredientes"],
    "nl": ["ingrediënten", "ingredienten", "samenstelling"],
    "pl": ["składniki", "skladniki", "skład", "sklad"],
    "ja": ["成分", "全成分", "配合成分"],
    "ko": ["전성분", "성분", "성분표"],
    "zh": ["成分", "配方成分", "成份"],
    "ar": ["المكونات", "مكونات", "التركيب"],
}

# Flat normalised set for fast O(1) lookups after stripping accents
def _strip_accents(text: str) -> str:
    """Remove combining diacritics so accented variants match bare ASCII."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_ALL_HEADINGS: frozenset[str] = frozenset(
    _strip_accents(h)
    for headings in INGREDIENT_HEADINGS.values()
    for h in headings
)


def is_ingredient_heading(text: str) -> bool:
    """
    Return True if *text* matches a known ingredient heading in any supported language.

    Comparison is case-insensitive and accent-insensitive. The text may contain
    surrounding whitespace or punctuation that is stripped before matching.

    Args:
        text: The visible label of a tab, button, or heading element.

    Returns:
        True if the text is recognised as an ingredient heading.
    """
    normalised = _strip_accents(text.strip().lower())
    # Exact match
    if normalised in _ALL_HEADINGS:
        return True
    # Contained match — heading label sometimes has extra chars, e.g. "Ingredients:"
    for heading in _ALL_HEADINGS:
        if heading and heading in normalised:
            return True
    return False


# ---------------------------------------------------------------------------
# INCI name detection
# ---------------------------------------------------------------------------

# INCI names are standardised international cosmetic ingredient names.
# They are almost always written in Latin characters (often all-caps in ingredient
# lists), do NOT contain sentence-level punctuation, and match a small set of
# structural patterns. They must be preserved as-is during translation.

_INCI_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9 /\-\(\)\.\+]*$"  # All-caps INCI style
    r"|^[A-Z][a-z]+([\- ][A-Za-z0-9\(\)]+)*$"  # Title-case Latin word(s)
)

# Non-INCI markers: if a token contains accented non-Latin characters it is
# almost certainly a translated label rather than an INCI name.
_NON_LATIN_RE = re.compile(r"[^\x00-\x7F]")


def is_inci_name(token: str) -> bool:
    """
    Heuristic: return True if *token* looks like an INCI ingredient name.

    INCI names use Latin characters and follow standard chemical naming
    conventions. They are preserved verbatim during translation.

    Args:
        token: A single comma-separated ingredient token.

    Returns:
        True if the token appears to be an INCI name.
    """
    token = token.strip()
    if not token:
        return False
    # Contains non-Latin characters → likely a translated label, not INCI
    if _NON_LATIN_RE.search(token):
        return False
    return bool(_INCI_PATTERN.match(token))


# ---------------------------------------------------------------------------
# Language / translation detection
# ---------------------------------------------------------------------------

# Common English cosmetic/INCI stop-words. If a significant fraction of
# comma-separated tokens are recognised English/INCI words, translation is
# not needed. Non-Latin characters are the strongest signal that translation
# is required.

def needs_translation(ingredients_text: str) -> bool:
    """
    Heuristic: return True if *ingredients_text* is likely non-English and
    should be translated before storing.

    The check is conservative — it only flags text when there is a clear
    non-Latin or non-INCI signal, so pure INCI lists (which are already
    internationally standardised) are never unnecessarily flagged.

    Args:
        ingredients_text: The raw extracted ingredients string.

    Returns:
        True if the text should be translated.
    """
    if not ingredients_text or ingredients_text == "Not listed":
        return False

    # If the text contains CJK, Arabic, or other non-Latin characters,
    # translation is required.
    if re.search(r"[\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]", ingredients_text):
        return True

    # If more than half the tokens contain accented Latin characters (e.g. French,
    # German, Spanish labels interspersed with INCI names), translation is needed.
    tokens = [t.strip() for t in ingredients_text.split(",") if t.strip()]
    if not tokens:
        return False
    accented = sum(1 for t in tokens if _NON_LATIN_RE.search(t))
    return (accented / len(tokens)) > 0.2
