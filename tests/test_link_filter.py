"""
Unit tests for product link detection (step 2b of get-ingredients.md).

Tests confirm:
  - Known product URL patterns are classified as 'product'
  - Excluded segments (/blog, /about, etc.) produce 'excluded'
  - Query strings produce 'excluded'
  - Fragment anchors produce 'excluded'
  - External domains produce 'excluded'
  - Unknown on-domain paths produce 'collection'
"""
import pytest
from tests.helpers.link_filter import classify_link

BASE = "www.testbrand.com"


class TestProductPatterns:
    @pytest.mark.parametrize("href", [
        "/p/colour-cream-500ml",
        "/products/permanent-dye",
        "/product/toning-shampoo",
        "/professional-hair-products/bleach-kit",
        "/hair-colour/shade-5",
        "/hair-color/auburn",
        "/colour/permanent-5-0",
        "/color/vivid-red",
    ])
    def test_product_patterns_classified_as_product(self, href):
        assert classify_link(href, BASE) == "product"

    def test_absolute_product_url_same_domain(self):
        href = f"https://{BASE}/products/colour-cream"
        assert classify_link(href, BASE) == "product"


class TestExcludedSegments:
    @pytest.mark.parametrize("href", [
        "/brands/testbrand",
        "/c/hair",
        "/collections/all",
        "/category/hair-care",
        "/blog/colour-tips",
        "/about",
        "/about/us",
        "/search?q=dye",
    ])
    def test_excluded_segments_produce_excluded(self, href):
        assert classify_link(href, BASE) == "excluded"

    def test_query_string_produces_excluded(self):
        assert classify_link("/products/dye?colour=brown", BASE) == "excluded"

    def test_fragment_anchor_produces_excluded(self):
        assert classify_link("#ingredients", BASE) == "excluded"

    def test_product_path_with_fragment_excluded(self):
        assert classify_link("/products/dye#description", BASE) == "excluded"

    def test_external_domain_produces_excluded(self):
        assert classify_link("https://otherbrand.com/products/dye", BASE) == "excluded"

    def test_javascript_link_excluded(self):
        assert classify_link("javascript:void(0)", BASE) == "excluded"

    def test_empty_href_excluded(self):
        assert classify_link("", BASE) == "excluded"


class TestCollectionFallback:
    def test_unknown_path_returns_collection(self):
        assert classify_link("/our-range/hair", BASE) == "collection"

    def test_absolute_unknown_path_same_domain(self):
        href = f"https://{BASE}/our-range/hair"
        assert classify_link(href, BASE) == "collection"


class TestFixtureCollectionPage:
    """Validate expected classifications match the collection.html fixture."""

    LINKS = [
        ("/products/colour-cream", "product"),
        ("/products/toning-shampoo", "product"),
        ("/products/bleach-kit", "product"),
        ("/products/colour-brush", "product"),
        ("/about", "excluded"),
        ("/blog/tips", "excluded"),
        ("/products/colour-cream?sort=price", "excluded"),
        ("https://otherbrand.com/products/dye", "excluded"),
    ]

    @pytest.mark.parametrize("href,expected", LINKS)
    def test_collection_fixture_links(self, href, expected):
        assert classify_link(href, BASE) == expected
