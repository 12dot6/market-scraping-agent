"""
Unit tests for multilingual ingredient extraction helpers (step 3b–3d of get-ingredients.md).

Tests confirm:
  - Ingredient headings are recognised in all supported languages
  - Non-heading strings are not falsely matched
  - INCI names are correctly identified (preserved during translation)
  - Non-INCI labels (accented / non-Latin) are not misidentified as INCI
  - needs_translation() correctly flags non-English ingredient strings
  - Pure INCI lists are never flagged for translation
"""
import pytest
from tests.helpers.ingredient_extraction import (
    is_ingredient_heading,
    is_inci_name,
    needs_translation,
)


class TestIngredientHeadingDetection:

    @pytest.mark.parametrize("label", [
        # English
        "Ingredients",
        "INGREDIENTS",
        "ingredients",
        "Ingredient List",
        "Full Ingredient List",
        "INCI",
        # French
        "Ingrédients",
        "ingrédients",
        "Composition",
        # German
        "Inhaltsstoffe",
        "inhaltsstoffe",
        "Zutaten",
        # Spanish
        "Ingredientes",
        "Composición",
        "Composicion",
        # Italian
        "Ingredienti",
        "Composizione",
        # Portuguese
        "Ingredientes",
        "Composição",
        # Dutch
        "Ingrediënten",
        "Ingredienten",
        "Samenstelling",
        # Polish
        "Składniki",
        "Skladniki",
        "Skład",
        # Japanese
        "成分",
        "全成分",
        # Korean
        "전성분",
        "성분",
        # Chinese
        "配方成分",
        # Arabic
        "المكونات",
        "مكونات",
    ])
    def test_recognised_in_all_languages(self, label):
        assert is_ingredient_heading(label) is True

    @pytest.mark.parametrize("label", [
        # Labels with surrounding whitespace/punctuation still match
        "  Ingredients  ",
        "Ingredients:",
        "Composition:",
        "【成分】",
    ])
    def test_tolerates_surrounding_punctuation(self, label):
        assert is_ingredient_heading(label) is True

    @pytest.mark.parametrize("label", [
        "How to use",
        "Description",
        "Benefits",
        "Directions",
        "Product Details",
        "Ratings",
        "Add to basket",
        "",
        "Features",
    ])
    def test_non_heading_labels_not_matched(self, label):
        assert is_ingredient_heading(label) is False


class TestInciNameDetection:

    @pytest.mark.parametrize("token", [
        # All-caps INCI
        "AQUA",
        "SODIUM LAURETH SULFATE",
        "CETEARYL ALCOHOL",
        "P-PHENYLENEDIAMINE",
        "HC RED 3",
        "PARFUM",
        # Title-case INCI
        "Aqua",
        "Cetearyl Alcohol",
        "Phenoxyethanol",
        "Hydrogen Peroxide",
    ])
    def test_recognises_inci_names(self, token):
        assert is_inci_name(token) is True

    @pytest.mark.parametrize("token", [
        # Contains non-ASCII characters → not INCI
        "Öl",                # German (umlaut)
        "Huile d'argan",     # French description
        "ماء",               # Arabic (water)
        "水",                # Chinese (water)
        "아쿠아",             # Korean
        "",
    ])
    def test_non_inci_tokens_rejected(self, token):
        assert is_inci_name(token) is False


class TestNeedsTranslation:

    @pytest.mark.parametrize("text", [
        # Japanese
        "水、グリセリン、フェノキシエタノール",
        # Korean
        "정제수, 글리세린, 페녹시에탄올",
        # Chinese
        "水,甘油,苯氧乙醇",
        # Arabic
        "ماء، جلسرين، فينوكسي إيثانول",
        # Heavily accented French labels mixed with some INCI
        "Aqua, Huile d'argan, Beurre de Karité, Cetearyl Alcohol",
    ])
    def test_non_english_text_flagged(self, text):
        assert needs_translation(text) is True

    @pytest.mark.parametrize("text", [
        # Pure INCI all-caps
        "AQUA, SODIUM LAURETH SULFATE, CETEARYL ALCOHOL, PARFUM",
        # Pure INCI title-case
        "Aqua, Cetearyl Alcohol, Phenoxyethanol, Citric Acid",
        # Mixed but majority INCI
        "Aqua, Hydrogen Peroxide, P-Phenylenediamine, Resorcinol, Parfum",
        # Edge cases
        "Not listed",
        "",
    ])
    def test_english_or_inci_text_not_flagged(self, text):
        assert needs_translation(text) is False

    def test_none_like_values_not_flagged(self):
        assert needs_translation("Not listed") is False
        assert needs_translation("") is False
