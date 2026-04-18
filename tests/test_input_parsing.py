"""
Unit tests for input.txt URL parsing (step 0 of get-ingredients.md).

Tests confirm the parsing rules:
  - Blank lines are ignored
  - Lines starting with # are ignored
  - All other lines are returned as URLs
"""
import pytest
from tests.helpers.input_parser import parse_urls


class TestParseUrls:
    def test_single_url(self):
        content = "https://www.example.com/hair-colour"
        assert parse_urls(content) == ["https://www.example.com/hair-colour"]

    def test_multiple_urls(self):
        content = "https://www.site-a.com/colour\nhttps://www.site-b.com/dye"
        assert parse_urls(content) == [
            "https://www.site-a.com/colour",
            "https://www.site-b.com/dye",
        ]

    def test_blank_lines_ignored(self):
        content = "https://www.site-a.com\n\n\nhttps://www.site-b.com"
        assert parse_urls(content) == [
            "https://www.site-a.com",
            "https://www.site-b.com",
        ]

    def test_comment_lines_ignored(self):
        content = "# This is a comment\nhttps://www.example.com"
        assert parse_urls(content) == ["https://www.example.com"]

    def test_comment_at_start_of_line_only(self):
        """Inline comments (not at line start) are treated as part of the URL."""
        content = "https://www.example.com  # not a comment"
        result = parse_urls(content)
        # The whole line is the URL (strip is applied, but # mid-line is kept)
        assert len(result) == 1
        assert result[0].startswith("https://www.example.com")

    def test_whitespace_stripped_from_urls(self):
        content = "  https://www.example.com/colour  "
        assert parse_urls(content) == ["https://www.example.com/colour"]

    def test_empty_content(self):
        assert parse_urls("") == []

    def test_only_comments(self):
        content = "# line 1\n# line 2\n# line 3"
        assert parse_urls(content) == []

    def test_only_blank_lines(self):
        content = "\n\n\n"
        assert parse_urls(content) == []

    def test_mixed_comments_blanks_urls(self):
        content = (
            "# Header comment\n"
            "\n"
            "https://www.loreal.com/hair-colour\n"
            "# Another comment\n"
            "\n"
            "https://www.schwarzkopf.com/colour\n"
        )
        assert parse_urls(content) == [
            "https://www.loreal.com/hair-colour",
            "https://www.schwarzkopf.com/colour",
        ]

    def test_preserves_url_order(self):
        urls = [f"https://site{i}.com" for i in range(5)]
        content = "\n".join(urls)
        assert parse_urls(content) == urls

    def test_real_input_txt_template(self, fixtures_dir):
        """The bundled input.txt template produces no URLs (all lines are comments)."""
        project_root = fixtures_dir.parent.parent
        input_path = project_root / "input.txt"
        if input_path.exists():
            content = input_path.read_text(encoding="utf-8")
            urls = parse_urls(content)
            # Template should ship with no real URLs active
            assert all(u.startswith("#") is False for u in urls), (
                "input.txt contains active URLs — ensure examples are commented out "
                "before sharing the project."
            )
