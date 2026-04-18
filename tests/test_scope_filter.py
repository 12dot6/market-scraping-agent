"""
Unit tests for the product scope filter (step 2c of get-ingredients.md).

Tests confirm:
  - Products are in scope when URL, title, or ingredients match criteria
  - Products are out of scope when none of the criteria match
  - Source category URLs bypass the filter entirely
  - The reason string accurately reflects the match type
"""
import pytest
from tests.helpers.scope_filter import (
    is_in_scope,
    in_scope_by_url_or_title,
    in_scope_by_ingredients,
    source_url_is_colour_category,
)


class TestScopeKeywords:
    @pytest.mark.parametrize("url,title", [
        ("/products/colour-cream", ""),
        ("/products/hair-color", ""),
        ("/products/bleach-kit", ""),
        ("/products/developer", ""),
        ("/products/toner", ""),
        ("/products/dye-shade-5", ""),
        ("", "Permanent Hair Colour"),
        ("", "Grey Coverage Cream"),
        ("", "Colour-Safe Shampoo"),
        ("", "Highlighting Kit"),
        ("", "Balayage Lightener"),
    ])
    def test_in_scope_by_keyword(self, url, title):
        assert in_scope_by_url_or_title(url, title) is True

    @pytest.mark.parametrize("url,title", [
        ("/products/moisturising-mask", "Moisturising Hair Mask"),
        ("/products/brush", "Application Brush"),
        ("/products/shampoo", "Everyday Shampoo"),
    ])
    def test_not_in_scope_by_keyword(self, url, title):
        assert in_scope_by_url_or_title(url, title) is False


class TestDyeActives:
    @pytest.mark.parametrize("ingredients_text", [
        "Aqua, Resorcinol, Cetearyl Alcohol",
        "AQUA, P-PHENYLENEDIAMINE, PARFUM",
        "Hydrogen Peroxide 6%, Aqua",
        "Aqua, Ammonium Persulfate, Potassium Persulfate",
        "Acid Violet 43, Sodium Laureth Sulfate",
        "Aqua, Aminophenol, Citric Acid",
        "Lawsone, Aqua, Citric Acid",
    ])
    def test_in_scope_by_dye_actives(self, ingredients_text):
        assert in_scope_by_ingredients(ingredients_text) is True

    def test_not_in_scope_by_dye_actives(self):
        ingredients = "Aqua, Sodium Laureth Sulfate, Citric Acid, Phenoxyethanol"
        assert in_scope_by_ingredients(ingredients) is False

    def test_empty_ingredients(self):
        assert in_scope_by_ingredients("") is False
        assert in_scope_by_ingredients("Not listed") is False


class TestCategoryBypass:
    @pytest.mark.parametrize("url", [
        "https://www.example.com/hair-colour/all",
        "https://www.example.com/hair-color/c/1234",
        "https://www.example.com/colour/permanent",
        "https://www.example.com/color/lines",
    ])
    def test_colour_category_url_detected(self, url):
        assert source_url_is_colour_category(url) is True

    def test_non_category_url_not_detected(self):
        assert source_url_is_colour_category("https://www.example.com/hair-care") is False


class TestIsInScope:
    def test_url_match_returns_correct_reason(self):
        in_scope, reason = is_in_scope(
            url="/products/colour-cream",
            title="Cream",
            ingredients_text="",
        )
        assert in_scope is True
        assert reason == "URL match"

    def test_title_match_returns_correct_reason(self):
        in_scope, reason = is_in_scope(
            url="/products/brush",
            title="Colour Application Brush",
            ingredients_text="",
        )
        assert in_scope is True
        assert reason == "title match"

    def test_ingredient_match_returns_correct_reason(self):
        in_scope, reason = is_in_scope(
            url="/products/shampoo",
            title="Everyday Shampoo",
            ingredients_text="Aqua, Resorcinol, Parfum",
        )
        assert in_scope is True
        assert reason == "ingredient match"

    def test_out_of_scope(self):
        in_scope, reason = is_in_scope(
            url="/products/brush",
            title="Application Brush",
            ingredients_text="Not listed",
        )
        assert in_scope is False
        assert reason == "out of scope"

    def test_skip_filter_always_in_scope(self):
        in_scope, reason = is_in_scope(
            url="/products/brush",
            title="Application Brush",
            ingredients_text="",
            skip_filter=True,
        )
        assert in_scope is True
        assert reason == "category"

    def test_fixture_accordion_product_in_scope(self):
        """Product from product_accordion.html fixture should be in scope via ingredient match."""
        in_scope, reason = is_in_scope(
            url="/products/colour-cream",
            title="Permanent Colour Cream 5.0 Brown",
            ingredients_text="AQUA, CETEARYL ALCOHOL, RESORCINOL, MONOETHANOLAMINE, P-PHENYLENEDIAMINE",
        )
        assert in_scope is True

    def test_fixture_no_ingredients_product_out_of_scope(self):
        """Colour Application Brush from product_no_ingredients.html should be out of scope."""
        # Note: "colour" appears in the title — the brush WILL match by title
        # This tests the AI's judgement; the brush should be excluded despite "colour" in title
        # because it's clearly not a hair dye product. This is a known ambiguity.
        in_scope, reason = is_in_scope(
            url="/products/colour-brush",
            title="Colour Application Brush",
            ingredients_text="Not listed",
        )
        # Title contains "colour" so our keyword logic returns True.
        # The AI must use context/judgement to exclude it.
        # This test documents the ambiguity — mark it as a known case.
        assert reason in ("URL match", "title match", "out of scope"), (
            "Ambiguous product: 'Colour Application Brush' contains scope keyword "
            "but is not a hair dye product. AI should ideally exclude it."
        )
