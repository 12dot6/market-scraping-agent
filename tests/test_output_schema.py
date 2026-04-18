"""
Post-run output schema validators (steps 7 + 8 of get-ingredients.md).

These tests validate files that already exist in output/ after a real
/get-ingredients run. They are skipped gracefully when no outputs are present.

Run after any scraping session:
    pytest tests/test_output_schema.py -v

Use as a regression gate:
    pytest tests/ -v --tb=short
"""
import csv
import re
from pathlib import Path

import pytest
import yaml

OUTPUT_DIR = Path(__file__).parent.parent / "output"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
REQUIRED_FRONTMATTER_KEYS = {"title", "source_urls", "scraped", "product_count", "excluded_count"}
SLUG_RE = re.compile(r"^[a-z][a-z0-9-]+-\d{4}-\d{2}-\d{2}\.md$")
SUMMARY_TABLE_HEADER_RE = re.compile(
    r"\|\s*product name\s*\|.*ingredients available.*\|.*in-scope reason.*\|",
    re.IGNORECASE,
)


def _md_files():
    """Collect all .md files in output/ (excluding archive/ and .gitkeep)."""
    if not OUTPUT_DIR.exists():
        return []
    return [
        p for p in OUTPUT_DIR.glob("*.md")
        if p.name != ".gitkeep"
    ]


def _extract_frontmatter(content: str) -> dict:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


# ---------------------------------------------------------------------------
# MD file tests — parametrized over every file in output/
# ---------------------------------------------------------------------------

@pytest.fixture(params=_md_files(), ids=lambda p: p.name)
def md_file(request) -> Path:
    return request.param


@pytest.mark.skipif(not _md_files(), reason="No output MD files found — run /get-ingredients first")
class TestMarkdownSchema:
    def test_file_slug_format(self, md_file):
        """File name must be lowercase-hyphen-slug with a YYYY-MM-DD date suffix."""
        assert SLUG_RE.match(md_file.name), (
            f"{md_file.name!r} does not match expected slug pattern "
            f"'<slug>-YYYY-MM-DD.md'"
        )

    def test_frontmatter_present(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        assert content.startswith("---"), (
            f"{md_file.name} has no YAML frontmatter (must start with ---)"
        )

    def test_frontmatter_is_valid_yaml(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        assert fm, f"{md_file.name} frontmatter could not be parsed as YAML"

    def test_frontmatter_required_keys(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        missing = REQUIRED_FRONTMATTER_KEYS - set(fm.keys())
        assert not missing, (
            f"{md_file.name} frontmatter is missing keys: {missing}"
        )

    def test_source_urls_is_list(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        assert isinstance(fm.get("source_urls"), list), (
            f"{md_file.name}: 'source_urls' must be a list, got {type(fm.get('source_urls'))}"
        )

    def test_source_urls_non_empty(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        assert len(fm.get("source_urls", [])) > 0, (
            f"{md_file.name}: 'source_urls' list must not be empty"
        )

    def test_product_count_is_positive_integer(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        assert isinstance(fm.get("product_count"), int) and fm["product_count"] >= 0, (
            f"{md_file.name}: 'product_count' must be a non-negative integer"
        )

    def test_excluded_count_is_non_negative_integer(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        assert isinstance(fm.get("excluded_count"), int) and fm["excluded_count"] >= 0, (
            f"{md_file.name}: 'excluded_count' must be a non-negative integer"
        )

    def test_scraped_date_format(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        scraped = str(fm.get("scraped", ""))
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", scraped), (
            f"{md_file.name}: 'scraped' must be ISO 8601 date (YYYY-MM-DD), got {scraped!r}"
        )

    def test_product_sections_present(self, md_file):
        """Each product must have a ## heading."""
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        product_count = fm.get("product_count", 0)
        sections = re.findall(r"^##\s+.+", content, re.MULTILINE)
        # Exclude the Excluded Products section from the count
        product_sections = [s for s in sections if "Excluded Products" not in s]
        assert len(product_sections) >= product_count, (
            f"{md_file.name}: expected {product_count} product sections, "
            f"found {len(product_sections)}"
        )

    def test_summary_table_present(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        assert SUMMARY_TABLE_HEADER_RE.search(content), (
            f"{md_file.name} is missing the summary table "
            f"(expected header row with 'product name | ingredients available | in-scope reason')"
        )

    def test_summary_table_has_data_rows(self, md_file):
        content = md_file.read_text(encoding="utf-8")
        fm = _extract_frontmatter(content)
        product_count = fm.get("product_count", 0)
        # Count pipe-delimited rows that are not header/separator rows
        table_rows = re.findall(r"^\|[^-|][^|]*\|", content, re.MULTILINE)
        # Subtract 1 for the header row
        data_rows = len(table_rows) - 1
        assert data_rows >= product_count, (
            f"{md_file.name}: summary table has {data_rows} data rows "
            f"but product_count is {product_count}"
        )


# ---------------------------------------------------------------------------
# CSV tests
# ---------------------------------------------------------------------------

CSV_PATH = OUTPUT_DIR / "ingredients-master.csv"


@pytest.mark.skipif(
    not CSV_PATH.exists(),
    reason="ingredients-master.csv not found — run /get-ingredients first",
)
class TestIngredientsCsv:
    def test_csv_has_correct_headers(self):
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            headers = csv.DictReader(f).fieldnames
        assert list(headers) == ["ingredient", "internal_name", "count"], (
            f"CSV headers are {headers!r}, expected ['ingredient', 'internal_name', 'count']"
        )

    def test_csv_sorted_descending_by_count(self):
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        counts = [int(r["count"]) for r in rows]
        assert counts == sorted(counts, reverse=True), (
            "CSV is not sorted descending by count"
        )

    def test_csv_no_zero_counts(self):
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        zero_rows = [r["ingredient"] for r in rows if int(r["count"]) <= 0]
        assert not zero_rows, f"CSV contains rows with count <= 0: {zero_rows}"

    def test_csv_no_duplicate_ingredients(self):
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        lower_names = [r["ingredient"].lower() for r in rows]
        duplicates = [n for n in lower_names if lower_names.count(n) > 1]
        assert not duplicates, (
            f"CSV contains duplicate ingredient entries (case-insensitive): "
            f"{list(set(duplicates))}"
        )

    def test_csv_all_counts_are_integers(self):
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            assert row["count"].isdigit(), (
                f"Non-integer count for {row['ingredient']!r}: {row['count']!r}"
            )

    def test_csv_no_empty_ingredient_names(self):
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        empty = [i for i, r in enumerate(rows, 1) if not r["ingredient"].strip()]
        assert not empty, f"CSV has empty ingredient names on lines: {empty}"

    def test_csv_alphabetical_within_same_count(self):
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        from itertools import groupby
        for count, group in groupby(rows, key=lambda r: r["count"]):
            names = [r["ingredient"].lower() for r in group]
            assert names == sorted(names), (
                f"Ingredients with count={count} are not in alphabetical order: {names}"
            )
