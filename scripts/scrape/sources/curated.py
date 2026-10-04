"""Source: hand-researched new records (source-data/phase2/curated_records.csv).

For businesses no directory carries, found by research (first batch: food vendors on
the 2026 Salida Farmers Market list that were missing from our data). The research
lives in the CSV itself: one row per business, a `Status` decision, and a
`Source URLs` cell backing the stated values.

Only rows with Status `add` become records. `market-only` (real, but sells only at
markets/online, so there's no place of its own to pin) and `skip` rows stay in the CSV
as the research record, so the same name isn't researched twice.

Confidence rule as everywhere: a cell is filled only when a source states it.
Latitude/Longitude are optional; empty -> `build.fill_geography` geocodes the address.
Provenance label: "curated". Corrections to records that already exist belong in
overrides.csv instead.
"""
from __future__ import annotations

import csv
import os
from typing import List

from ..normalize import clean_url, phone, zipcode
from ..schema import ATTR_TO_COLUMN, Market

SOURCE = "curated"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PATH = os.path.join(REPO, "source-data", "phase2", "curated_records.csv")

NORMALIZE = {"phone": phone, "website": clean_url, "facebook": clean_url,
             "instagram": clean_url, "zip": zipcode}


def parse(rows: List[dict]) -> List[Market]:
    out: List[Market] = []
    for r in rows:
        if (r.get("Status") or "").strip().lower() != "add":
            continue
        name = (r.get("Business Name") or "").strip()
        if not name:
            continue
        m = Market(source=SOURCE, category=(r.get("Category") or "").strip())
        for attr, col in ATTR_TO_COLUMN.items():
            val = (r.get(col) or "").strip()
            if attr in NORMALIZE and val:
                val = NORMALIZE[attr](val)
            m.set(attr, val, SOURCE)
        try:
            lat, lng = float(r.get("Latitude") or ""), float(r.get("Longitude") or "")
            m.latitude, m.longitude, m.geo_source = lat, lng, "source"
        except ValueError:
            pass
        m.source_id = (r.get("Source URLs") or "").split(";")[0].strip()
        m.source_updated = (r.get("Researched") or "").strip()
        out.append(m)
    return out


def load(path: str = PATH) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def fetch(path: str = PATH) -> List[Market]:
    return parse(load(path))
