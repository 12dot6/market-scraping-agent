"""
Reference implementation of the input.txt URL parsing logic (step 0 of get-ingredients.md).

Rules:
- Blank lines are ignored.
- Lines starting with # are ignored (comments).
- All other lines are treated as URLs.
"""


def parse_urls(content: str) -> list[str]:
    """Extract valid URLs from input.txt content."""
    urls = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)
    return urls
