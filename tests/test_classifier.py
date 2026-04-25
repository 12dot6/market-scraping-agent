"""
Unit tests for backend/services/classifier.py

Tests cover:
  - _parse_response_text: JSON extraction with and without markdown fences
  - classify(): valid response, not-in-scope response, error handling (never raises)
"""
import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

# Patch the module-level _load_mapping call before importing classifier
_FAKE_MAPPING = "PPD: p-Phenylenediamine\nRES: Resorcinol\n"

with patch("pathlib.Path.read_text", return_value=_FAKE_MAPPING):
    from backend.services.classifier import _normalize_result, _parse_response_text, classify


# ---------------------------------------------------------------------------
# _parse_response_text
# ---------------------------------------------------------------------------

class TestParseResponseText:
    def _valid_json(self):
        return {
            "in_scope": True,
            "scope_reason": "Contains oxidative dye actives",
            "components": {"OXIDATIVE DYE SYSTEM": ["p-Phenylenediamine"]},
            "dye_actives": ["p-Phenylenediamine"],
            "internal_names": {"p-Phenylenediamine": "PPD"},
        }

    def test_plain_json(self):
        text = json.dumps(self._valid_json())
        result = _parse_response_text(text)
        assert result["in_scope"] is True
        assert result["dye_actives"] == ["p-Phenylenediamine"]

    def test_strips_json_code_fence(self):
        text = "```json\n" + json.dumps(self._valid_json()) + "\n```"
        result = _parse_response_text(text)
        assert result["in_scope"] is True

    def test_strips_plain_code_fence(self):
        text = "```\n" + json.dumps(self._valid_json()) + "\n```"
        result = _parse_response_text(text)
        assert result["scope_reason"] == "Contains oxidative dye actives"

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_response_text("not valid json")

    def test_not_in_scope_response(self):
        payload = {
            "in_scope": False,
            "scope_reason": "Not a dye product",
            "components": {},
            "dye_actives": [],
            "internal_names": {},
        }
        result = _parse_response_text(json.dumps(payload))
        assert result["in_scope"] is False
        assert result["components"] == {}


class TestNormalizeResult:
    def test_fills_missing_schema_keys_with_defaults(self):
        result = _normalize_result({"in_scope": True})
        assert result == {
            "in_scope": True,
            "scope_reason": "",
            "components": {},
            "dye_actives": [],
            "internal_names": {},
        }


# ---------------------------------------------------------------------------
# classify() — contract and error handling
# ---------------------------------------------------------------------------

class TestClassify:
    def _run(self, coro):
        return asyncio.run(coro)

    def _make_mock_response(self, payload: dict) -> MagicMock:
        mock_content = MagicMock()
        mock_content.text = json.dumps(payload)
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    def test_returns_valid_structure_on_success(self):
        payload = {
            "in_scope": True,
            "scope_reason": "Contains p-Phenylenediamine",
            "components": {"OXIDATIVE DYE SYSTEM": ["p-Phenylenediamine", "Resorcinol"]},
            "dye_actives": ["p-Phenylenediamine"],
            "internal_names": {"p-Phenylenediamine": "PPD"},
        }
        with patch("backend.services.classifier._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = self._make_mock_response(payload)
            mock_get_client.return_value = mock_client
            result = self._run(classify("Excellence Crème", "https://example.com", "p-Phenylenediamine, Resorcinol, Water"))

        assert result["in_scope"] is True
        assert "components" in result
        assert "dye_actives" in result
        assert "internal_names" in result

    def test_returns_in_scope_false_for_not_listed(self):
        payload = {
            "in_scope": False,
            "scope_reason": "Ingredients not listed",
            "components": {},
            "dye_actives": [],
            "internal_names": {},
        }
        with patch("backend.services.classifier._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = self._make_mock_response(payload)
            mock_get_client.return_value = mock_client
            result = self._run(classify("Some Product", "https://example.com", "Not listed"))

        assert result["in_scope"] is False

    def test_never_raises_on_api_error(self):
        with patch("backend.services.classifier._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("API timeout")
            mock_get_client.return_value = mock_client
            result = self._run(classify("Product", "https://example.com", "Water"))

        assert result["in_scope"] is False
        assert "Classification error" in result["scope_reason"]
        assert result["components"] == {}
        assert result["dye_actives"] == []
        assert result["internal_names"] == {}

    def test_never_raises_on_json_parse_error(self):
        mock_content = MagicMock()
        mock_content.text = "I cannot parse this"
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        with patch("backend.services.classifier._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_get_client.return_value = mock_client
            result = self._run(classify("Product", "https://example.com", "Water"))

        assert result["in_scope"] is False
        assert "Classification error" in result["scope_reason"]

    def test_api_called_with_correct_model(self):
        payload = {"in_scope": False, "scope_reason": "x", "components": {}, "dye_actives": [], "internal_names": {}}
        with patch("backend.services.classifier._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = self._make_mock_response(payload)
            mock_get_client.return_value = mock_client
            self._run(classify("P", "https://x.com", "Water"))
            call_kwargs = mock_client.messages.create.call_args[1]

        assert call_kwargs["model"] == "claude-sonnet-4-6"
        assert call_kwargs["max_tokens"] == 600

    def test_system_has_two_cached_blocks(self):
        payload = {"in_scope": False, "scope_reason": "x", "components": {}, "dye_actives": [], "internal_names": {}}
        with patch("backend.services.classifier._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = self._make_mock_response(payload)
            mock_get_client.return_value = mock_client
            self._run(classify("P", "https://x.com", "Water"))
            call_kwargs = mock_client.messages.create.call_args[1]

        system = call_kwargs["system"]
        assert len(system) == 2
        for block in system:
            assert block.get("cache_control") == {"type": "ephemeral"}

    def test_normalizes_missing_fields_from_model_response(self):
        payload = {"in_scope": False}
        with patch("backend.services.classifier._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = self._make_mock_response(payload)
            mock_get_client.return_value = mock_client
            result = self._run(classify("P", "https://x.com", "Water"))

        assert result["scope_reason"] == ""
        assert result["components"] == {}
        assert result["dye_actives"] == []
        assert result["internal_names"] == {}
