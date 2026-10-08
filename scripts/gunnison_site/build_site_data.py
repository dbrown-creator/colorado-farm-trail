#!/usr/bin/env python3
"""Build the data file for the Gunnison Valley Provides prototype (gunnison-valley/).

Reads whatever the Colorado producers dataset holds for the area, so the site grows as
the research lands; rebuild with this one script:

  python scripts/gunnison_site/build_site_data.py [--inputs <repo checkout>]
         [--counties Gunnison,Hinsdale] [--producers <colorado-producers-data checkout>]

Sources, in priority order:
  1. Phase 2 statewide build  source-data/phase2/co_farmers_markets_all_raw.csv
     (the pipeline's merged output; hand-researched records and overrides are already
     folded in), rows whose County is in --counties (default: Gunnison).
  2. The public producers data set  colorado-producers-data/data/producers.csv (other
     schema), for places in the area that Phase 2 does not carry. Skipped if absent.
  3. Verification results  source-data/phase2/enrichment/results/  ("checked on" date).
Phase 3 market-vendor lists (names only, not yet researched) are NOT shown as places.
They are counted, so the site can say honestly how many leads are still being verified.

Output: gunnison-valley/data/providers.json
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from scrape.normalize import name_key  # noqa: E402
from build_map_data import social_url, website_url  # noqa: E402

_args = sys.argv[1:]


def arg(flag, default):
    return _args[_args.index(flag) + 1] if flag in _args else default


INPUTS = os.path.abspath(arg("--inputs", REPO))
AREA_COUNTIES = {c.strip() for c in arg("--counties", "Gunnison").split(",") if c.strip()}
PRODUCERS = os.path.abspath(arg("--producers", os.path.join(REPO, "..", "colorado-producers-data")))
if not os.path.isdir(PRODUCERS):  # inside a .claude/worktrees/<name> checkout
    PRODUCERS = os.path.abspath(os.path.join(REPO, "..", "..", "..", "..", "colorado-producers-data"))
RAW = os.path.join(INPUTS, "source-data", "phase2", "co_farmers_markets_all_raw.csv")
RESULTS = os.path.join(INPUTS, "source-data", "phase2", "enrichment", "results")
VENDORS = os.path.join(INPUTS, "source-data", "phase3", "market_vendor_lists", "all_vendors.csv")
OUT = os.path.join(REPO, "gunnison-valley", "data", "providers.json")
CHECKS = os.path.join(REPO, "gunnison-valley", "data", "site-checks.json")

# Phase 3 vendor lists carry the market's city and, once the county-labeling task lands,
# a County column. Until then these cities identify the Gunnison County markets.
AREA_MARKET_CITIES = {"gunnison", "crested butte", "mount crested butte", "mt. crested butte",
                      "almont", "pitkin", "marble"}

# Left off this prototype on purpose (name keys). Mountain Roots Food Project is the
# organization the prototype is being shown to; it is not listed on its own pitch.
EXCLUDE = {name_key("Mountain Roots Food Project")}

SOURCE_LABELS = {
    "colorado_proud": "Colorado Proud", "colorado_proud_farm_fresh": "Colorado Proud",
    "colorado_proud_finder": "Colorado Proud", "chaffee_provides": "Chaffee Provides",
    "curated": "Farmers market vendor lists, checked by hand",
    "cfma": "Colorado Farmers Market Association", "usda": "USDA Local Food Directories",
    "official-site": "Provider's own website", "dedup-decision": "Reviewed by hand",
    "census-geocoder": "US Census geocoder", "producers-dataset": "Colorado producers data set",
}

TYPES = {
    "farm": ("Farms & Ranches", {"On-Farm / Ranch Sales", "CSA Farm", "U-Pick", "Roadside Market",
                                 "Garden Center / Greenhouse", "Meat Producer & Packer",
                                 "Farm Products (online)", "Agritourism"}),
    "market": ("Markets & Shops", {"Farmers' Market", "Winery", "Grocery Store", "Bakery",
                                   "Food Maker", "Farm Store"}),
    "assistance": ("Food Assistance", {"Food Bank", "Community Food Hub"}),
    "dining": ("Restaurants & Caterers", {"Restaurant", "Caterer"}),
    "community": ("Community & Education", {"Organization", "Food Hub"}),
}
# The producers data set uses coarser map groups; map them back to the labels above.
GROUP_TO_CATEGORY = {"Farms & Ranches": "On-Farm / Ranch Sales", "Wineries": "Winery",
                     "Shops & Grocers": "Grocery Store", "Farmers' Markets": "Farmers' Market"}

OFFERINGS = [
    ("veggies", "Veggies", r"veggie|vegetable|produce|greens|lettuce|tomato|squash|potato|"
                           r"beet|carrot|pepper|kale|broccoli|asparagus|mushroom|chile|onion"),
    ("fruit", "Fruit", r"fruit|apple|apricot|peach|cherr|berr|melon|plum|\bpears?\b|grape"),
    ("beef-meat", "Beef & Meat", r"beef|meat|pork|lamb|bison|sausage|jerky|cattle"),
    ("poultry-eggs", "Poultry & Eggs", r"poultry|\beggs?\b|chicken|turkey|duck"),
    ("dairy", "Dairy", r"dairy|milk|cheese|yogurt|butter|kefir"),
    ("flowers", "Flowers", r"flower|lavender|bouquet"),
    ("spices-garlic", "Spices & Garlic", r"spice|garlic|herb"),
    ("staples", "Pantry Staples", r"staple|honey|grain|flour|bread|baked|preserve|jam"),
]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def split_list(s):
    return [p.strip() for p in (s or "").split(",") if p.strip()]


def yes(s):
    return (s or "").strip().lower() in ("yes", "y", "true", "1")


def load_status():
    out = {}
    if os.path.isdir(RESULTS):
        for fn in os.listdir(RESULTS):
            if fn.endswith(".json"):
                try:
                    r = json.load(open(os.path.join(RESULTS, fn), encoding="utf-8"))
                except (ValueError, OSError):
                    continue
                out[r.get("id") or fn[:-5]] = r
    return out


def from_raw(row):
    lat = row.get("Latitude")
    return {
        "name": row["Business Name"], "categories": split_list(row["Category"]),
        "address": row["Address"], "city": row["City"], "county": row["County"], "zip": row["Zip"],
        "phone": row["Phone"], "callFirst": yes(row["Call first?"]),
        "website": website_url(row["Website"]) or "", "email": row["Email"],
        "facebook": social_url(row["Facebook"], "https://facebook.com/") or "",
        "instagram": social_url(row["Instagram"], "https://instagram.com/") or "",
        "hours": row["Hours"], "monthsOpen": split_list(row["Months Open"]),
        "products": row["Products"], "organic": yes(row["Certified Organic"]),
        "snap": yes(row["SNAP"]), "ada": yes(row["ADA Accessible"]), "notes": row["Notes"],
        "lat": float(lat) if lat else None, "lng": float(row["Longitude"]) if lat else None,
        "sources": [s for s in row["Source"].split("+") if s],
    }


def from_producers(row):
    cats = split_list(row.get("detailed categories", "")) or [
        GROUP_TO_CATEGORY.get(row["category"], "Organization")]
    lat = row.get("lat")
    return {
        "name": row["name"], "categories": cats, "address": row["address"], "city": row["city"],
        "county": row["county"], "zip": row["zip"], "phone": row["phone"], "callFirst": False,
        "website": website_url(row["website"]) or "", "email": row["email"],
        "facebook": social_url(row["facebook"], "https://facebook.com/") or "",
        "instagram": social_url(row["instagram"], "https://instagram.com/") or "",
        "hours": row["hours"], "monthsOpen": split_list(row["months"]), "products": row["products"],
        "organic": yes(row["organic"]), "snap": yes(row["snap"]), "ada": False, "notes": "",
        "lat": float(lat) if lat else None, "lng": float(row["lng"]) if lat else None,
        "sources": ["producers-dataset"],
    }


def facets(p):
    cats = set(p["categories"])
    p["types"] = [k for k, (_, labels) in TYPES.items() if cats & labels] or ["community"]
    text = " ".join([p["products"], " ".join(p["categories"])]).lower()
    p["offerings"] = [k for k, _, rx in OFFERINGS if re.search(rx, text)]


def vendor_leads(listed):
    """Farm-signal vendors on Gunnison-area market lists (Phase 3): unresearched leads.

    Only vendors the list builder flagged as likely farms/food producers (Farm Signal
    strong or maybe) count; craft, art and clothing vendors on the same lists do not."""
    if not os.path.exists(VENDORS):
        return {"count": 0, "markets": []}
    rows = list(csv.DictReader(open(VENDORS, encoding="utf-8-sig")))
    has_county = bool(rows) and "County" in rows[0]
    hit = [r for r in rows if (r.get("County") in AREA_COUNTIES if has_county
                               else r["Market City"].strip().lower() in AREA_MARKET_CITIES)
           and r.get("Farm Signal") in ("strong", "maybe")
           and name_key(r["Vendor Name"]) not in EXCLUDE | listed]  # already a listing: not a lead
    return {"count": len(hit), "names": sorted(r["Vendor Name"] for r in hit),
            "markets": sorted({r["Market"] for r in hit}),
            "byCountyColumn": has_county}


def main():
    status = load_status()
    checks = json.load(open(CHECKS, encoding="utf-8")) if os.path.exists(CHECKS) else {"places": {}}
    providers = {}
    for row in csv.DictReader(open(RAW, encoding="utf-8-sig")):
        if row["County"] in AREA_COUNTIES and name_key(row["Business Name"]) not in EXCLUDE:
            p = from_raw(row)
            providers[name_key(p["name"])] = p
    from_phase2 = len(providers)

    prod_csv = os.path.join(PRODUCERS, "data", "producers.csv")
    extra = 0
    if os.path.exists(prod_csv):
        for row in csv.DictReader(open(prod_csv, encoding="utf-8-sig")):
            if (row["county"] in AREA_COUNTIES and name_key(row["name"]) not in providers
                    and name_key(row["name"]) not in EXCLUDE):
                providers[name_key(row["name"])] = from_producers(row)
                extra += 1

    out = []
    for p in providers.values():
        sid = f"{slug(p['name'])}__{slug(p['city'] or 'gunnison-county')}"
        st = status.get(sid) or next(
            (r for r in status.values() if name_key(r.get("name", "")) == name_key(p["name"])), None)
        p["status"] = st.get("status", "unknown") if st else "unverified"
        p["verified"] = st.get("checked", "") if st else ""
        p["id"] = slug(p["name"])
        p["town"] = p["city"] or f"{p['county']} County"
        chk = checks["places"].get(p["id"])
        if chk:  # hand-run check against the provider's own website (site-checks.json)
            p["checkNotes"] = chk["notes"]
            if chk["status"] != "unverified":
                p["status"], p["verified"] = chk["status"], checks["checked"]
            for k, v in chk.get("fixes", {}).items():
                if not p.get(k):
                    p[k] = v
        if not p["address"]:  # town-only record: its coordinates are a town centre, not the place
            p["lat"] = p["lng"] = None
        p["sourceLabels"] = list(dict.fromkeys(SOURCE_LABELS.get(s, s) for s in p["sources"]))
        facets(p)
        out.append(p)
    seen = {}
    for p in out:
        n = seen.get(p["id"], 0)
        seen[p["id"]] = n + 1
        if n:
            p["id"] = f"{p['id']}-{n + 1}"
    out.sort(key=lambda p: p["name"].lower())

    meta = {
        "generated": dt.date.today().isoformat(), "count": len(out),
        "counties": sorted(AREA_COUNTIES),
        "types": {k: v[0] for k, v in TYPES.items()},
        "offerings": {k: label for k, label, _ in OFFERINGS}, "months": MONTHS,
        "vendorLeads": vendor_leads(set(providers)),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "providers": out}, fh, ensure_ascii=False, indent=1)
    print(f"Wrote {len(out)} places ({from_phase2} from Phase 2, {extra} only in the producers "
          f"data set) -> {os.path.relpath(OUT, REPO)}")
    print("  vendor-list leads (not shown as places):", meta["vendorLeads"]["count"])
    print("  no coordinates:", [p["name"] for p in out if p["lat"] is None])


if __name__ == "__main__":
    main()
