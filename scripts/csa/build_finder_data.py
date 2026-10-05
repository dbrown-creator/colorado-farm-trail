"""Build the CSA finder's data file: csa/csa-data.js

Inputs : data-compiled/phase2/csa.json            (confirmed CSAs, from build_csa.py)
         data-compiled/phase2/co_farmers_markets_all_mymaps.csv  (town + ZIP centers)
Output : csa/csa-data.js  ->  window.CSA_DATA = {built, csas[], towns{}, zips{}}

Every pickup site gets coordinates, tagged with how precise they are:
  exact  - the farm posted a street address and the Census geocoder placed it
  farm   - an on-farm pickup, placed at the farm's own pin
  town   - only a town was posted; placed at that town's center (approximate)
  none   - could not be placed (never guessed); the finder lists it without a distance

Geocoder answers are cached in .cache/csa_geocode.json so reruns only look up new
addresses (see docs: incremental builds).
Run:  python scripts/csa/build_finder_data.py
"""
import csv, json, re, statistics, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.scrape import geocode as gc  # noqa: E402

CACHE = ROOT / ".cache/csa_geocode.json"
OUT = ROOT / "csa/csa-data.js"


def load_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def centers():
    towns, zips = defaultdict(list), defaultdict(list)
    path = ROOT / "data-compiled/phase2/co_farmers_markets_all_mymaps.csv"
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        try:
            lat, lon = float(r["Latitude"]), float(r["Longitude"])
        except ValueError:
            continue
        city = (r["City"] or "").strip().lower()
        if city:
            towns[city].append((lat, lon))
        z = re.match(r"\d{5}", r["Zip"] or "")
        if z:
            zips[z.group(0)].append((lat, lon))
    med = lambda pts: [round(statistics.median(p[0] for p in pts), 4), round(statistics.median(p[1] for p in pts), 4)]
    return {k: med(v) for k, v in towns.items()}, {k: med(v) for k, v in zips.items()}


def geocode(cache, address, town):
    key = f"{address}|{town}".lower()
    if key not in cache:
        res = gc.geocode_address(address, town, "")
        cache[key] = [res[0], res[1]] if res else None
    return cache[key]


def main():
    cache = load_cache()
    towns, zips = centers()
    csas, stats = [], defaultdict(int)
    for r in json.loads((ROOT / "data-compiled/phase2/csa.json").read_text(encoding="utf-8")):
        lat = float(r["lat"]) if r.get("lat") else None
        lon = float(r["lon"]) if r.get("lon") else None
        if lat is None and r.get("address"):
            hit = geocode(cache, r["address"], r["city"])
            if hit:
                lat, lon = hit
        if lat is None and r["city"].lower() in towns:
            lat, lon = towns[r["city"].lower()]
            stats["farm placed at town center"] += 1
        pickups = []
        for p in r.get("pickup_sites") or []:
            prec, plat, plon = "none", None, None
            if p.get("on_farm") and lat is not None:
                prec, plat, plon = "farm", lat, lon
            elif p.get("address"):
                hit = geocode(cache, p["address"], p.get("town") or r["city"])
                if hit:
                    prec, (plat, plon) = "exact", hit
            if prec == "none" and (p.get("town") or "").lower() in towns:
                prec = "town"
                plat, plon = towns[p["town"].lower()]
            stats[f"pickup {prec}"] += 1
            pickups.append({k: p.get(k) for k in ("name", "address", "town", "day", "time", "on_farm")}
                            | {"lat": plat, "lon": plon, "prec": prec})
        d = r.get("delivery") or {}
        csas.append({
            "id": r["id"], "name": r["name"], "city": r["city"], "county": r["county"],
            "lat": lat, "lon": lon, "website": r.get("website") or "",
            "signup_url": r.get("signup_url") or "", "signup_opens": r.get("signup_opens"),
            "status": r.get("csa_status") or "unknown",
            "season_start": r.get("season_start"), "season_end": r.get("season_end"),
            "season_precision": r.get("season_precision"),
            "share_types": r.get("share_types") or [], "frequency": r.get("frequency"),
            "price": r.get("price"), "snap": r.get("snap_accepted"),
            "pickups": pickups,
            "delivery": {"offered": d.get("offered"), "towns": d.get("towns") or [], "zips": d.get("zips") or [],
                         "radius": d.get("radius_miles"), "fee": d.get("fee"), "details": d.get("details") or ""},
        })
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=0), encoding="utf-8")
    from datetime import date
    payload = {"built": date.today().isoformat(), "csas": csas, "towns": towns, "zips": zips}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.CSA_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")
    print(f"{len(csas)} CSAs, {len(towns)} towns, {len(zips)} zips -> {OUT.relative_to(ROOT)}")
    print("no farm coords:", [c["name"] for c in csas if c["lat"] is None])
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
