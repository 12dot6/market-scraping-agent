"""
Unit tests for the CSV merge logic (steps 5b + 8 of get-ingredients.md).

Tests cover:
  - Loading the mapping file
  - Internal name resolution (all 5 priority levels)
  - Merging new ingredients into an empty CSV
  - Incrementing counts for existing ingredients
  - Preserving internal_name for existing rows on increment
  - Sort order: descending count, then alphabetical
  - Case-insensitive deduplication
  - Full round-trip: merge → write → read back
"""
import csv
import pytest
from pathlib import Path
from tests.helpers.csv_merge import (
    load_mapping,
    load_existing_csv,
    resolve_internal_name,
    merge,
    write_csv,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mapping(mapping_path):
    return load_mapping(mapping_path)


@pytest.fixture
def existing(existing_csv_path):
    return load_existing_csv(existing_csv_path)


# ---------------------------------------------------------------------------
# load_mapping
# ---------------------------------------------------------------------------

class TestLoadMapping:
    def test_header_skipped(self, mapping):
        # "Ingredients" is the header column name — should not appear as a key
        assert "ingredients" not in mapping

    def test_known_key_present(self, mapping):
        assert "resorcinol" in mapping

    def test_known_internal_name_correct(self, mapping):
        assert mapping["resorcinol"] == "Test Dye Anchor"

    def test_normalised_key_strips_trailing_number(self, mapping):
        # "Steareth-21" → normalised to "steareth"
        assert "steareth" in mapping

    def test_all_keys_lowercased(self, mapping):
        for key in mapping:
            assert key == key.lower(), f"Key not lowercased: {key!r}"


# ---------------------------------------------------------------------------
# resolve_internal_name — all 5 priority levels
# ---------------------------------------------------------------------------

class TestResolveInternalName:
    def test_p1_exact_match(self, mapping):
        result = resolve_internal_name("Resorcinol", mapping)
        assert result == "Test Dye Anchor"

    def test_p1_exact_match_case_insensitive(self, mapping):
        assert resolve_internal_name("RESORCINOL", mapping) == "Test Dye Anchor"
        assert resolve_internal_name("resorcinol", mapping) == "Test Dye Anchor"

    def test_p2_scraped_contains_key(self, mapping):
        # "p-Phenylenediamine" contains "phenylenediamine" (a mapping key)
        result = resolve_internal_name("p-Phenylenediamine", mapping)
        assert result == "Test Chromamine"

    def test_p3_key_contains_scraped(self, mapping):
        # "Acid Violet" (key in mapping) contains "acid violet" (scraped name)
        result = resolve_internal_name("Acid Violet 43", mapping)
        assert result == "Test Acid Dye Violet"

    def test_p4_normalised_match(self, mapping):
        # "Steareth-2" normalises to "steareth", matches mapping key "steareth-2"
        result = resolve_internal_name("Steareth-2", mapping)
        assert result in ("Test Emulso 2", "Test Emulso 21")  # either Steareth-2 or Steareth-21

    def test_p4_exact_normalised_match_prefers_correct_entry(self, mapping):
        # "Steareth-21" should resolve to Test Emulso 21 (exact normalised match)
        result = resolve_internal_name("Steareth-21", mapping)
        assert result == "Test Emulso 21"

    def test_p5_no_match_returns_empty(self, mapping):
        result = resolve_internal_name("Xanthan Gum", mapping)
        assert result == ""

    def test_longer_key_preferred_on_tie(self, mapping):
        # When both P2 and P3 candidates exist, longer key wins
        # "Acid Violet 43" — "acid violet" (key in mapping, len 11) should be preferred
        result = resolve_internal_name("Acid Violet 43", mapping)
        assert result == "Test Acid Dye Violet"


# ---------------------------------------------------------------------------
# load_existing_csv
# ---------------------------------------------------------------------------

class TestLoadExistingCsv:
    def test_loads_known_row(self, existing):
        assert "aqua" in existing

    def test_count_is_integer(self, existing):
        for row in existing.values():
            assert isinstance(row["count"], int)

    def test_keys_are_lowercased(self, existing):
        for key in existing:
            assert key == key.lower()

    def test_empty_path_returns_empty_dict(self, tmp_path):
        missing = tmp_path / "nonexistent.csv"
        assert load_existing_csv(missing) == {}


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

class TestMerge:
    def test_new_ingredient_added(self, existing, mapping):
        run_counts = {"lawsone": {"ingredient": "Lawsone", "count": 3}}
        rows = merge(existing, run_counts, mapping)
        names = [r["ingredient"] for r in rows]
        assert "Lawsone" in names

    def test_existing_count_incremented(self, existing, mapping):
        run_counts = {"aqua": {"ingredient": "Aqua", "count": 5}}
        rows = merge(existing, run_counts, mapping)
        aqua = next(r for r in rows if r["ingredient"] == "Aqua")
        assert aqua["count"] == 15  # 10 existing + 5 new

    def test_existing_internal_name_preserved(self, existing, mapping):
        run_counts = {"aqua": {"ingredient": "Aqua", "count": 1}}
        rows = merge(existing, run_counts, mapping)
        aqua = next(r for r in rows if r["ingredient"] == "Aqua")
        assert aqua["internal_name"] == "Test Water"

    def test_new_row_gets_internal_name_from_mapping(self, existing, mapping):
        run_counts = {"resorcinol": {"ingredient": "Resorcinol", "count": 2}}
        rows = merge(existing, run_counts, mapping)
        row = next(r for r in rows if r["ingredient"] == "Resorcinol")
        assert row["internal_name"] == "Test Dye Anchor"

    def test_new_row_no_match_has_empty_internal_name(self, existing, mapping):
        run_counts = {"xanthan gum": {"ingredient": "Xanthan Gum", "count": 1}}
        rows = merge(existing, run_counts, mapping)
        row = next(r for r in rows if r["ingredient"] == "Xanthan Gum")
        assert row["internal_name"] == ""

    def test_sort_descending_by_count(self, existing, mapping):
        run_counts = {"resorcinol": {"ingredient": "Resorcinol", "count": 20}}
        rows = merge(existing, run_counts, mapping)
        counts = [r["count"] for r in rows]
        assert counts == sorted(counts, reverse=True)

    def test_sort_alphabetical_on_count_tie(self, mapping):
        existing = {
            "beta": {"ingredient": "Beta", "internal_name": "", "count": 5},
            "alpha": {"ingredient": "Alpha", "internal_name": "", "count": 5},
            "gamma": {"ingredient": "Gamma", "internal_name": "", "count": 5},
        }
        rows = merge(existing, {}, mapping)
        names = [r["ingredient"] for r in rows]
        assert names == ["Alpha", "Beta", "Gamma"]

    def test_case_insensitive_deduplication(self, mapping):
        # "AQUA" and "Aqua" should merge into one row
        existing = {"aqua": {"ingredient": "Aqua", "internal_name": "Test Water", "count": 5}}
        run_counts = {"aqua": {"ingredient": "AQUA", "count": 3}}
        rows = merge(existing, run_counts, mapping)
        aqua_rows = [r for r in rows if r["ingredient"].lower() == "aqua"]
        assert len(aqua_rows) == 1
        assert aqua_rows[0]["count"] == 8

    def test_empty_existing_creates_from_scratch(self, mapping):
        run_counts = {
            "aqua": {"ingredient": "Aqua", "count": 5},
            "resorcinol": {"ingredient": "Resorcinol", "count": 3},
        }
        rows = merge({}, run_counts, mapping)
        assert len(rows) == 2
        assert rows[0]["count"] >= rows[1]["count"]

    def test_merge_does_not_mutate_existing(self, existing, mapping):
        original_count = existing["aqua"]["count"]
        run_counts = {"aqua": {"ingredient": "Aqua", "count": 99}}
        merge(existing, run_counts, mapping)
        assert existing["aqua"]["count"] == original_count


# ---------------------------------------------------------------------------
# write_csv round-trip
# ---------------------------------------------------------------------------

class TestWriteCsv:
    def test_round_trip(self, tmp_path, existing, mapping):
        run_counts = {"resorcinol": {"ingredient": "Resorcinol", "count": 4}}
        rows = merge(existing, run_counts, mapping)

        output = tmp_path / "output" / "ingredients-master.csv"
        write_csv(rows, output)

        assert output.exists()
        with open(output, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            written = list(reader)

        assert written[0]["ingredient"] is not None
        assert int(written[0]["count"]) >= int(written[-1]["count"])

    def test_csv_has_correct_headers(self, tmp_path, mapping):
        rows = merge({}, {"aqua": {"ingredient": "Aqua", "count": 1}}, mapping)
        output = tmp_path / "test.csv"
        write_csv(rows, output)

        with open(output, newline="", encoding="utf-8") as f:
            headers = f.readline().strip().split(",")
        assert headers == ["ingredient", "internal_name", "count"]

    def test_creates_parent_directories(self, tmp_path, mapping):
        deep_path = tmp_path / "a" / "b" / "c" / "test.csv"
        write_csv([], deep_path)
        assert deep_path.exists()
