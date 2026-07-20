"""Orchestrate all sources -> dedupe/merge -> geocode gaps -> write CSVs.

Outputs (new files; Farm Fresh CSVs are left untouched):
  data/co_farmers_markets_all_mymaps.csv  : the 22 My Maps columns, import-ready
  data/co_farmers_markets_all_raw.csv     : same + source/geo_source/provenance audit

Run:
  python scripts/scrape/build.py              # uses no key (Colorado Proud + datashare)
  USDA_API_KEY=xxxx python scripts/scrape/build.py   # adds the rich USDA statewide pull
"""
from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrape import geocode
from scrape.merge import flag_possible_dups, merge
from scrape.normalize import in_colorado
from scrape.schema import COLUMNS, Market
from scrape.sources import cfma, colorado_proud, enrichment, usda

# PHASE 2 (in development — NOT the live product). Outputs are isolated under phase2/
# so they never touch the live Phase 1 file data-compiled/farm_fresh_directory_mymaps.csv.
# Canonical split: compiled map-ready CSV -> data-compiled/phase2/;
# full raw+provenance export -> source-data/phase2/.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
COMPILED_DIR = os.path.join(REPO, "data-compiled", "phase2")
SOURCE_DIR = os.path.join(REPO, "source-data", "phase2")


def collect() -> list:
    """Gather records from every available source, in priority order."""
    # Order = field-value priority (first source to fill a field wins):
    # Colorado Proud (vetted) > CFMA (rich, member-maintained) > USDA (broad, thin).
    # A later per-site enrichment pass can override any of these from the market's own
    # official website (see README "Field-value priority").
    records = []

    enr = enrichment.fetch()
    if enr:
        print(f"Official-site enrichment: {len(enr)} records (top priority)...", flush=True)
        records += enr

    print("Colorado Proud (ArcGIS)...", flush=True)
    records += colorado_proud.fetch()

    print("CFMA member markets (MarketWurks)...", flush=True)
    try:
        records += cfma.fetch()
    except Exception as e:
        print(f"  CFMA fetch failed: {e}")

    key = os.environ.get("USDA_API_KEY", "").strip()
    if key:
        print("USDA keyed API (statewide grid)...", flush=True)
        records += usda.fetch_api(key)
    else:
        print("USDA key absent -> keyless data_share only (thin).", flush=True)
        try:
            records += usda.parse_datashare(usda.fetch_datashare_raw())
        except Exception as e:
            print(f"  data_share failed: {e}")

    # TODO(enrichment): cfma.fetch(), curated.fetch(), per-site enrichment.
    return records


def fill_geography(markets: list) -> None:
    """Geocode missing coordinates and backfill county. Derived coords are flagged
    geo_source='census-geocoder'; source-provided coords are left as-is."""
    for m in markets:
        if m.latitude is None or not in_colorado(m.latitude, m.longitude):
            r = geocode.geocode_address(m.address, m.city, m.zip)
            if r and in_colorado(r[0], r[1]):
                m.latitude, m.longitude, county = r
                m.geo_source = "census-geocoder"
                if not m.county and county:
                    m.set("county", county, "census-geocoder")
        if not m.county and m.latitude is not None:
            county = geocode.county_for(m.latitude, m.longitude)
            if county:
                m.set("county", county, "census-geocoder")


def write(markets: list) -> None:
    os.makedirs(COMPILED_DIR, exist_ok=True)
    os.makedirs(SOURCE_DIR, exist_ok=True)
    mymaps = os.path.join(COMPILED_DIR, "co_farmers_markets_all_mymaps.csv")
    raw = os.path.join(SOURCE_DIR, "co_farmers_markets_all_raw.csv")

    with open(mymaps, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for m in markets:
            w.writerow(m.to_mymaps_row())

    extra = ["Source", "Geo Source", "Possible Dup Of", "Provenance"]
    with open(raw, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS + extra)
        w.writeheader()
        for m in markets:
            row = m.to_mymaps_row()
            row["Source"] = m.source
            row["Geo Source"] = m.geo_source
            row["Possible Dup Of"] = m.dup_hint
            row["Provenance"] = json.dumps(m.provenance, separators=(",", ":"))
            w.writerow(row)

    print(f"Wrote {len(markets)} markets:\n  {mymaps}\n  {raw}")


def main() -> None:
    records = collect()
    markets = merge(records)
    fill_geography(markets)
    flag_possible_dups(markets)
    markets.sort(key=lambda m: (m.city.lower(), m.business_name.lower()))
    write(markets)
    dups = sum(1 for m in markets if m.dup_hint)
    if dups:
        print(f"{dups} markets flagged 'Possible Dup Of' for review (see raw CSV).")


if __name__ == "__main__":
    main()
