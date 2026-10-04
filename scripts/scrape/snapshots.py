"""Source snapshots: the parsed records of each network source, saved to disk.

`refresh_sources.py` is the only thing that talks to the sources; it writes one
snapshot per source under source-data/phase2/snapshots/. `build.py` reads the
snapshots and never touches the network for source data, so a rebuild repeats no
work. Snapshots hold parsed `Market` records (not raw responses), so after a parser
change, re-run the refresh for that source (Chaffee Provides re-parses its page cache
without recrawling).
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import os
from typing import List, Optional

from .schema import Market

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
SNAPSHOT_DIR = os.path.join(REPO, "source-data", "phase2", "snapshots")

# Build order = field-value priority (first source to fill a field wins).
NETWORK_SOURCES = ["colorado_proud", "cfma", "chaffee_provides", "colorado_proud_finder",
                   "usda_api", "usda_datashare"]

_FIELDS = {f.name for f in dataclasses.fields(Market)}


def path_for(name: str, snapshot_dir: str = SNAPSHOT_DIR) -> str:
    return os.path.join(snapshot_dir, f"{name}.json")


def save(name: str, records: List[Market], snapshot_dir: str = SNAPSHOT_DIR,
         fetched: Optional[str] = None) -> str:
    os.makedirs(snapshot_dir, exist_ok=True)
    doc = {
        "source": name,
        "fetched": fetched or _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "count": len(records),
        "records": [dataclasses.asdict(m) for m in records],
    }
    p = path_for(name, snapshot_dir)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return p


def load(name: str, snapshot_dir: str = SNAPSHOT_DIR):
    """-> (records, fetched timestamp), or ([], None) when there's no snapshot."""
    p = path_for(name, snapshot_dir)
    if not os.path.exists(p):
        return [], None
    with open(p, encoding="utf-8") as fh:
        doc = json.load(fh)
    recs = [Market(**{k: v for k, v in r.items() if k in _FIELDS}) for r in doc.get("records", [])]
    return recs, doc.get("fetched")


# ---- change report (the "approve" step) -------------------------------------------
# refresh_sources.py diffs each new snapshot against the previous one so a human can
# see exactly what a refresh would add or change before it's committed and built.

CHANGES_DIR = os.path.join(SNAPSHOT_DIR, "changes")
_COMPARE = ["business_name", "category", "address", "city", "county", "zip", "phone",
            "website", "email", "facebook", "instagram", "hours", "months_open",
            "products", "snap", "notes", "latitude", "longitude"]


def _key(m: Market) -> str:
    from .normalize import name_key
    # No source id (e.g. USDA data_share): name + town + category, since the same farm can
    # appear once per USDA directory.
    return m.source_id or "|".join([name_key(m.business_name), (m.city or "").strip().lower(),
                                    (m.category or "").strip().lower()])


def diff(old: List[Market], new: List[Market]) -> List[dict]:
    """Rows of {change: new|removed|changed, key, business_name, city, field, old, new}."""
    before = {_key(m): m for m in old}
    after = {_key(m): m for m in new}
    rows = []
    for k, m in after.items():
        if k not in before:
            rows.append({"change": "new", "key": k, "business_name": m.business_name,
                         "city": m.city, "field": "", "old": "", "new": ""})
            continue
        o = before[k]
        for f in _COMPARE:
            a, b = getattr(o, f), getattr(m, f)
            if (a or "") != (b or ""):
                rows.append({"change": "changed", "key": k, "business_name": m.business_name,
                             "city": m.city, "field": f, "old": a, "new": b})
    for k, m in before.items():
        if k not in after:
            rows.append({"change": "removed", "key": k, "business_name": m.business_name,
                         "city": m.city, "field": "", "old": "", "new": ""})
    return rows


def write_changes(name: str, rows: List[dict], changes_dir: str = CHANGES_DIR) -> str:
    import csv
    os.makedirs(changes_dir, exist_ok=True)
    p = os.path.join(changes_dir, f"{name}.csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["change", "key", "business_name", "city", "field", "old", "new"])
        w.writeheader()
        w.writerows(rows)
    return p
