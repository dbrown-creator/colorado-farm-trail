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
import re
import sys
from collections import Counter
from pathlib import Path

# A plausible social handle: letters/digits and . _ - only (no spaces, no "&", etc.)
# Instagram handles may contain dots (e.g. "abundant.spaces"), so dots are allowed.
_HANDLE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
# Scheme-less values that already start with one of these are URLs missing "https://".
_SOCIAL_DOMAINS = ("facebook.com/", "www.facebook.com/", "m.facebook.com/", "fb.com/",
                   "instagram.com/", "www.instagram.com/")

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data-compiled" / "farm_fresh_directory_mymaps.csv"
OUT = REPO / "data" / "markets.json"


def clean(value):
    """Trim whitespace; treat empty as None."""
    if value is None:
        return None
    v = value.strip()
    return v or None


def yes(value):
    """Map a Yes/No/blank cell to a boolean."""
    return (value or "").strip().lower() == "yes"


def split_list(value):
    """Split a comma-joined cell into a trimmed, de-blanked list."""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _has_scheme(v):
    vl = v.lower()
    return vl.startswith("http://") or vl.startswith("https://")


def _normalize_scheme(v):
    """Lowercase just the scheme (e.g. HTTPS://Foo -> https://Foo); host case is left alone."""
    for scheme in ("https://", "http://"):
        if v[:len(scheme)].lower() == scheme:
            return scheme + v[len(scheme):]
    return v


def website_url(value):
    """Normalize a website cell into a usable URL, or None.

    Most cells are bare domains missing the scheme (e.g. "bergharvest.com") --
    those become https://. Names, "none", or anything with spaces -> None.
    """
    v = clean(value)
    if not v or v.lower() == "none":
        return None
    if _has_scheme(v):
        return _normalize_scheme(v)
    if any(c.isspace() for c in v) or "." not in v:
        return None  # a business name, not a domain
    return "https://" + v


def social_url(value, base):
    """Normalize a social field (full URL or bare @handle) into a URL, or None.

    Bare cells that are actually business names (spaces, "&", apostrophes) can't
    form a valid link and return None rather than a broken URL.
    """
    v = clean(value)
    if not v:
        return None
    if any(c.isspace() for c in v):
        return None  # a business name, not a link
    if _has_scheme(v):
        return _normalize_scheme(v)
    # Scheme-less but already a social URL, e.g. "facebook.com/x", "www.instagram.com/x".
    if v.lower().startswith(_SOCIAL_DOMAINS):
        return "https://" + v
    # A bare handle, e.g. "@growinggardensboulder", "berg.harvest", "abundant.spaces".
    handle = v.lstrip("@").strip("/")
    if not handle or "/" in handle or not _HANDLE_RE.match(handle):
        return None
    return base + handle


def main():
    if not SRC.exists():
        sys.exit(f"ERROR: source CSV not found: {SRC}")

    with SRC.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    markets = []
    skipped = []
    for i, row in enumerate(rows, start=2):  # start=2 -> CSV line incl. header
        name = clean(row.get("Business Name"))
        category = clean(row.get("Category"))
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
    print("\nCategory distribution:")
    for cat, count in Counter(m["category"] for m in markets).most_common():
        print(f"  {count:3}  {cat}")


if __name__ == "__main__":
    main()
