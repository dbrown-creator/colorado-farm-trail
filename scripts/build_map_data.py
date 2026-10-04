#!/usr/bin/env python3
"""Build data/markets.json for the Leaflet webmap prototype (map.html).

Reads the live full directory CSV and emits a compact, browser-ready JSON array.
The CSVs contain multi-line quoted fields (long Notes/Products), so the browser
must NOT parse CSV directly -- this pre-generates clean JSON instead.

Run from the repo root:  python scripts/build_map_data.py

Stdlib only -- no third-party dependencies.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

# URL normalization is shared with the Phase 2 scraper (one copy, same rules).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape.normalize import social_url, website_url  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data-compiled" / "farm_fresh_directory_mymaps.csv"
OUT = REPO / "data" / "markets.json"


def _lf(value):
    """Normalize CRLF/CR line endings to LF.

    Git checks the source CSV out with native line endings, so on Windows the
    newlines *inside* quoted multi-line cells (Notes, Products) arrive as CRLF.
    Without this the same CSV builds a different markets.json per platform.
    """
    return value.replace("\r\n", "\n").replace("\r", "\n")


def clean(value):
    """Trim whitespace; treat empty as None."""
    if value is None:
        return None
    v = _lf(value).strip()
    return v or None


def yes(value):
    """Map a Yes/No/blank cell to a boolean."""
    return (value or "").strip().lower() == "yes"


def split_list(value):
    """Split a comma-joined cell into a trimmed, de-blanked list."""
    if not value:
        return []
    return [part.strip() for part in _lf(value).split(",") if part.strip()]


def main():
    if not SRC.exists():
        sys.exit(f"ERROR: source CSV not found: {SRC}")

    with SRC.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    markets = []
    skipped = []
    for i, row in enumerate(rows, start=2):  # start=2 -> CSV line incl. header
        name = clean(row.get("Business Name"))
        # Category may list several labels, primary first ("U-Pick, On-Farm / Ranch Sales").
        # `category` stays the primary (pin color/icon); `categories` drives the type filter.
        categories = split_list(row.get("Category"))
        category = categories[0] if categories else None
        try:
            lat = float(row["Latitude"])
            lng = float(row["Longitude"])
        except (TypeError, ValueError, KeyError):
            skipped.append((i, name, "bad/missing coordinates"))
            continue
        # Colorado sanity box -- catches mis-split rows where a stray value
        # landed in a coordinate column.
        if not (36.0 <= lat <= 41.5 and -110.0 <= lng <= -101.0):
            skipped.append((i, name, f"coords outside CO ({lat},{lng})"))
            continue
        if not name or not category:
            skipped.append((i, name, "missing name/category"))
            continue

        markets.append(
            {
                "name": name,
                "category": category,
                "categories": categories,
                "address": clean(row.get("Address")),
                "city": clean(row.get("City")),
                "county": clean(row.get("County")),
                "phone": clean(row.get("Phone")),
                "callFirst": yes(row.get("Call first?")),
                "website": website_url(row.get("Website")),
                "email": clean(row.get("Email")),
                "facebook": social_url(row.get("Facebook"), "https://facebook.com/"),
                "instagram": social_url(row.get("Instagram"), "https://instagram.com/"),
                "hours": clean(row.get("Hours")),
                "monthsOpen": split_list(row.get("Months Open")),
                "products": split_list(row.get("Products")),
                "organic": yes(row.get("Certified Organic")),
                "snap": yes(row.get("SNAP")),
                "ada": yes(row.get("ADA Accessible")),
                "notes": clean(row.get("Notes")),
                # Stores/markets/restaurants carrying a wholesale grower's products.
                # Semicolon-separated, since entries can contain commas.
                "whereToGet": [p.strip() for p in (clean(row.get("Where to Get It")) or "").split(";")
                               if p.strip()],
                "lat": lat,
                "lng": lng,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        json.dump(markets, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")

    # Summary
    print(f"Read {len(rows)} rows from {SRC.relative_to(REPO)}")
    print(f"Wrote {len(markets)} markets -> {OUT.relative_to(REPO)}")
    print(f"Skipped {len(skipped)} rows")
    for line_no, name, reason in skipped:
        print(f"  - line {line_no}: {name or '(no name)'} -> {reason}")
    print("\nCategory distribution (primary / listed under):")
    primary = Counter(m["category"] for m in markets)
    for cat, count in Counter(c for m in markets for c in m["categories"]).most_common():
        print(f"  {primary.get(cat, 0):3} / {count:3}  {cat}")


if __name__ == "__main__":
    main()
