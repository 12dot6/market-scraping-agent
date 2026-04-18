"""
Reference implementation of the CSV merge logic (steps 5b + 8 of get-ingredients.md).

This module is the canonical Python implementation used for unit testing.
The AI must produce outputs that match this logic.
"""

import csv
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _normalise(name: str) -> str:
    """Lowercase and strip trailing hyphens/numbers (e.g. 'Steareth-21' → 'steareth')."""
    return re.sub(r"[-\s\d]+$", "", name.lower()).strip()


# ---------------------------------------------------------------------------
# Mapping file
# ---------------------------------------------------------------------------

def load_mapping(mapping_path: Path) -> dict[str, str]:
    """
    Load mapped-ingredients.txt into {key: internal_name}.
    Stores both the exact lowercased key and the normalised key so that
    exact matches (e.g. 'steareth-21') take priority over normalised ones
    ('steareth') when resolving via resolve_internal_name.
    Format: 'Ingredient Name | Internal Name' (pipe-delimited, first line header).
    """
    mapping: dict[str, str] = {}
    lines = mapping_path.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:  # skip header
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        lower_key = parts[0].strip().lower()
        internal = parts[1].strip()
        norm_key = _normalise(lower_key)
        if norm_key and norm_key != lower_key:
            mapping[norm_key] = internal
        if lower_key:
            mapping[lower_key] = internal
    return mapping


# ---------------------------------------------------------------------------
# Internal name resolution (5-level priority)
# ---------------------------------------------------------------------------

def resolve_internal_name(ingredient: str, mapping: dict[str, str]) -> str:
    """
    Resolve internal_name for a new ingredient using 5-level priority
    (as specified in get-ingredients.md step 8):

      1. Exact case-insensitive match
      2. Scraped name contains a mapping key as substring
      3. Mapping key contains the scraped name as substring
      4. Strip trailing numbers/hyphens from both and compare (normalised)
      5. No match → return empty string

    When multiple keys match at the same priority level, prefer the longer key.
    """
    lower = ingredient.lower()
    norm = _normalise(ingredient)

    # Priority 1: exact match on normalised key
    if lower in mapping:
        return mapping[lower]
    if norm in mapping:
        return mapping[norm]

    # Priorities 2–4: collect (priority, key_length, internal_name) candidates
    candidates: list[tuple[int, int, str]] = []

    for key, internal_name in mapping.items():
        key_norm = _normalise(key)

        if key in lower:                        # P2: scraped contains key
            candidates.append((2, len(key), internal_name))
        elif lower in key:                      # P3: key contains scraped
            candidates.append((3, len(key), internal_name))
        elif key_norm and norm and key_norm == norm:  # P4: normalised match
            candidates.append((4, len(key), internal_name))

    if candidates:
        # Best = lowest priority number, then longest key for ties
        candidates.sort(key=lambda x: (x[0], -x[1]))
        return candidates[0][2]

    return ""  # P5: no match


# ---------------------------------------------------------------------------
# CSV load / merge / write
# ---------------------------------------------------------------------------

def load_existing_csv(csv_path: Path) -> dict[str, dict]:
    """
    Load ingredients-master.csv into {ingredient.lower(): row_dict}.
    Returns empty dict if the file does not exist.
    """
    if not csv_path.exists():
        return {}

    existing: dict[str, dict] = {}
    with open(csv_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            existing[row["ingredient"].lower()] = {
                "ingredient": row["ingredient"],
                "internal_name": row.get("internal_name", ""),
                "count": int(row["count"]),
            }
    return existing


def merge(
    existing: dict[str, dict],
    run_counts: dict[str, dict],
    mapping: dict[str, str],
) -> list[dict]:
    """
    Merge run_counts into existing in memory and return sorted rows.

    run_counts format: {ingredient.lower(): {"ingredient": str, "count": int}}

    Sort: descending by count, then alphabetically by ingredient for ties.
    """
    merged = {k: dict(v) for k, v in existing.items()}  # shallow copy

    for lower_key, item in run_counts.items():
        if lower_key in merged:
            merged[lower_key]["count"] += item["count"]
            # internal_name preserved from existing — do not overwrite
        else:
            internal_name = resolve_internal_name(item["ingredient"], mapping)
            merged[lower_key] = {
                "ingredient": item["ingredient"],
                "internal_name": internal_name,
                "count": item["count"],
            }

    return sorted(
        merged.values(),
        key=lambda r: (-r["count"], r["ingredient"].lower()),
    )


def write_csv(rows: list[dict], output_path: Path) -> None:
    """Write sorted rows to output_path as CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ingredient", "internal_name", "count"])
        writer.writeheader()
        writer.writerows(rows)
