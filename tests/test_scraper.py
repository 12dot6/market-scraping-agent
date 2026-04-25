"""
Unit tests for backend/services/scraper.py

These tests cover the pure-Python helpers and the error-handling contract
of scrape(). Live browser tests require the Docker environment with Playwright
chromium installed.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.scraper import _extract_name, scrape


# ---------------------------------------------------------------------------
# _extract_name
# ---------------------------------------------------------------------------

class TestExtractName:
    def test_strips_dash_suffix(self):
        assert _extract_name("L'Oreal Colorista - Shop Hair Colour", "") == "L'Oreal Colorista"

    def test_strips_pipe_suffix(self):
        assert _extract_name("Excellence Crème | L'Oreal Paris", "") == "Excellence Crème"

    def test_strips_em_dash_suffix(self):
        assert _extract_name("Nutrisse Colour – Garnier UK", "") == "Nutrisse Colour"

    def test_no_suffix_returns_full_title(self):
        assert _extract_name("Formulation Wiki", "") == "Formulation Wiki"

    def test_empty_title_falls_back_to_h1(self):
        assert _extract_name("", "Nutrisse Colour") == "Nutrisse Colour"

    def test_both_empty_returns_empty(self):
        assert _extract_name("", "") == ""

    def test_h1_used_only_when_title_empty(self):
        assert _extract_name("Title - Site", "H1 Text") == "Title"


# ---------------------------------------------------------------------------
# scrape() — error handling contract
# ---------------------------------------------------------------------------

class TestScrapeErrorContract:
    """scrape() must never raise; always return the expected dict shape."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_returns_not_listed_on_exception(self):
        with patch("backend.services.scraper.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__.side_effect = Exception("network error")
            result = self._run(scrape("https://example.com/product"))
        assert result["url"] == "https://example.com/product"
        assert result["ingredients_raw"] == "Not listed"
        assert "error" in result

    def test_result_shape_on_success(self):
        """Verify dict always has url, name, ingredients_raw keys on success path."""
        mock_page = AsyncMock()
        mock_page.title = AsyncMock(return_value="Product Name - Site")
        mock_page.inner_text = AsyncMock(return_value="Product Name")
        mock_page.evaluate = AsyncMock(side_effect=[None, "WATER, ALCOHOL"])
        mock_page.goto = AsyncMock()
        mock_page.set_default_timeout = MagicMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("backend.services.scraper.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_ap.return_value.__aexit__ = AsyncMock(return_value=False)
            result = self._run(scrape("https://example.com/product"))

        assert "url" in result
        assert "name" in result
        assert "ingredients_raw" in result
        mock_playwright.chromium.launch.assert_awaited_once_with(headless=True)
        mock_page.set_default_timeout.assert_called_once_with(30_000)

    def test_returns_not_listed_when_js_returns_none(self):
        """If ONE_SHOT_JS returns null/None, ingredients_raw should be 'Not listed'."""
        mock_page = AsyncMock()
        mock_page.title = AsyncMock(return_value="Product")
        mock_page.inner_text = AsyncMock(return_value="Product")
        mock_page.evaluate = AsyncMock(side_effect=[None, None])
        mock_page.goto = AsyncMock()
        mock_page.set_default_timeout = MagicMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("backend.services.scraper.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_ap.return_value.__aexit__ = AsyncMock(return_value=False)
            result = self._run(scrape("https://example.com/no-ingredients"))

        assert result["ingredients_raw"] == "Not listed"

    def test_browser_closed_when_mid_flow_exception_occurs(self):
        """Browser is closed even when an exception happens after launch."""
        mock_page = AsyncMock()
        mock_page.title = AsyncMock(side_effect=Exception("title failed"))
        mock_page.goto = AsyncMock()
        mock_page.set_default_timeout = MagicMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("backend.services.scraper.async_playwright") as mock_ap:
            mock_ap.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_ap.return_value.__aexit__ = AsyncMock(return_value=False)
            result = self._run(scrape("https://example.com/mid-flow-error"))

        assert result["ingredients_raw"] == "Not listed"
        assert "error" in result
        mock_browser.close.assert_awaited_once()
