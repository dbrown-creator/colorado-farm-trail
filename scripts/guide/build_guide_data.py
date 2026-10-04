"""Build guide/guide-data.js for the local food guide draft.

Reads the supply-network pilot (source-data/supply-network/{nodes,edges}.csv),
the farm-trail listings (data/markets.json, plus the Phase 2 compiled CSV for
day-plan stops), events (source-data/events/events.csv) and day plans
(source-data/guide/plans.json), and writes one JS file the static guide loads. Town coordinates are town centroids, so per-business
distances are approximate ("food miles" between towns, not addresses).

    python scripts/guide/build_guide_data.py
"""
import csv
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NET = ROOT / "source-data" / "supply-network"
OUT = ROOT / "guide" / "guide-data.js"
EVENTS = ROOT / "source-data" / "events" / "events.csv"
PLANS = ROOT / "source-data" / "guide" / "plans.json"
LISTINGS = ROOT / "data-compiled" / "phase2" / "co_farmers_markets_all_mymaps.csv"

# Town -> (region, lat, lng). Statewide/unknown entries have no point.
TOWNS = {
    # Denver metro
    "Denver": ("Denver Metro", 39.7392, -104.9903), "Denver metro": ("Denver Metro", 39.7392, -104.9903),
    "DIA": ("Denver Metro", 39.8561, -104.6737), "Aurora": ("Denver Metro", 39.7294, -104.8319),
    "Lakewood": ("Denver Metro", 39.7047, -105.0814), "Golden": ("Denver Metro", 39.7555, -105.2211),
    "Wheat Ridge": ("Denver Metro", 39.7661, -105.0772), "Littleton": ("Denver Metro", 39.6133, -105.0166),
    "Morrison": ("Denver Metro", 39.6536, -105.1911), "Northglenn": ("Denver Metro", 39.8961, -104.9811),
    "Thornton": ("Denver Metro", 39.8680, -104.9719), "Westminster": ("Denver Metro", 39.8367, -105.0372),
    "Brighton": ("Denver Metro", 39.9853, -104.8205),
    # Boulder County
    "Boulder": ("Boulder County", 40.0150, -105.2705), "Longmont": ("Boulder County", 40.1672, -105.1019),
    "Louisville": ("Boulder County", 39.9778, -105.1319), "Lafayette": ("Boulder County", 39.9936, -105.0897),
    "Lyons": ("Boulder County", 40.2247, -105.2714), "Niwot": ("Boulder County", 40.1039, -105.1708),
    "Erie": ("Boulder County", 40.0503, -105.0500),
    # Northern Colorado
    "Fort Collins": ("Northern Colorado", 40.5853, -105.0844), "Loveland": ("Northern Colorado", 40.3978, -105.0750),
    "Berthoud": ("Northern Colorado", 40.3083, -105.0811), "Estes Park": ("Northern Colorado", 40.3772, -105.5217),
    "Bellvue": ("Northern Colorado", 40.6264, -105.1711), "Laporte": ("Northern Colorado", 40.6264, -105.1394),
    "Greeley": ("Northern Colorado", 40.4233, -104.7091), "Kersey": ("Northern Colorado", 40.3875, -104.5619),
    # Mountains & Summit
    "Breckenridge": ("Summit & Mountains", 39.4817, -106.0384), "Frisco": ("Summit & Mountains", 39.5744, -106.0975),
    "Dillon": ("Summit & Mountains", 39.6303, -106.0434), "Granby": ("Summit & Mountains", 40.0861, -105.9395),
    "Grand Lake": ("Summit & Mountains", 40.2522, -105.8231), "Idaho Springs": ("Summit & Mountains", 39.7425, -105.5136),
    "Twin Lakes": ("Summit & Mountains", 39.0819, -106.3822), "Buena Vista": ("Summit & Mountains", 38.8422, -106.1311),
    # Roaring Fork
    "Aspen": ("Roaring Fork", 39.1911, -106.8175), "Basalt": ("Roaring Fork", 39.3689, -107.0328),
    "Carbondale": ("Roaring Fork", 39.4022, -107.2112), "New Castle": ("Roaring Fork", 39.5728, -107.5362),
    "Silt": ("Roaring Fork", 39.5486, -107.6562), "Glenwood Springs": ("Roaring Fork", 39.5505, -107.3248),
    "Snowmass Village": ("Roaring Fork", 39.2130, -106.9378), "Snowmass": ("Roaring Fork", 39.3297, -106.9853),
    # Western Slope
    "Grand Junction": ("Western Slope", 39.0639, -108.5506), "Palisade": ("Western Slope", 39.1103, -108.3509),
    "Clifton": ("Western Slope", 39.0819, -108.4598), "Delta": ("Western Slope", 38.7422, -108.0690),
    "Montrose": ("Western Slope", 38.4783, -107.8762), "Ridgway": ("Western Slope", 38.1528, -107.7562),
    "Paonia": ("Western Slope", 38.8683, -107.5920), "Hotchkiss": ("Western Slope", 38.7997, -107.7192),
    "Crawford": ("Western Slope", 38.7044, -107.6084), "North Fork Valley": ("Western Slope", 38.83, -107.65),
    "Western Slope": ("Western Slope", None, None),
    "Gunnison": ("Western Slope", 38.5458, -106.9253), "Crested Butte": ("Western Slope", 38.8697, -106.9878),
    # Southwest
    "Durango": ("Southwest", 37.2753, -107.8801), "Hesperus": ("Southwest", 37.2956, -108.0412),
    "Cortez": ("Southwest", 37.3489, -108.5859), "Dove Creek": ("Southwest", 37.7661, -108.9059),
    "Telluride": ("Southwest", 37.9375, -107.8123),
    # Northwest
    "Steamboat Springs": ("Northwest", 40.4850, -106.8317), "Yampa Valley": ("Northwest", 40.45, -106.9),
    "Meeker": ("Northwest", 40.0375, -107.9131),
    # South & San Luis Valley
    "Hooper": ("South & San Luis Valley", 37.7453, -105.8775), "Walsenburg": ("South & San Luis Valley", 37.6242, -104.7803),
    "Colorado Springs": ("South & San Luis Valley", 38.8339, -104.8214), "Black Forest": ("South & San Luis Valley", 39.0131, -104.7008),
    "Larkspur": ("South & San Luis Valley", 39.2286, -104.8872),
    # Eastern Plains
    "Holyoke": ("Eastern Plains", 40.5844, -102.3024), "Haxtun": ("Eastern Plains", 40.6411, -102.6293),
    "Fort Morgan": ("Eastern Plains", 40.2503, -103.7999), "Brush": ("Eastern Plains", 40.2589, -103.6233),
    "Roggen": ("Eastern Plains", 40.1661, -104.3699),
    # Out of state
    "Lusk, WY": ("Neighboring states", 42.7625, -104.4522),
}
STATEWIDE = {"Colorado", "Multiple", "Front Range", "unknown", ""}

TYPE_LABEL = {
    "farm": "Farm & ranch", "maker": "Maker", "distributor": "Distributor & food hub",
    "restaurant": "Restaurant", "retail": "Shop & grocer", "market": "Market",
}


def slug(s):
    s = s.lower().replace("’", "").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s.encode("ascii", "ignore").decode())
    return s.strip("-")


def miles(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2
         + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def year(d):
    m = re.match(r"(\d{4})", d or "")
    return int(m.group(1)) if m else None


def load_events():
    if not EVENTS.exists():
        return []
    out = []
    for r in csv.DictReader(open(EVENTS, encoding="utf-8-sig")):
        out.append({
            "id": slug(r["Event"]), "name": r["Event"], "kind": r["Kind"], "town": r["Town"],
            "region": r["Region"], "venue": r["Venue"], "season": r["Season"],
            "start": r["Start"] or None, "end": r["End"] or None, "recur": r["Recurrence"],
            "status": r["Status"], "host": r["Host"], "url": r["Website"], "desc": r["Description"],
        })
    return out


def listing_place(name, listings):
    """A day-plan stop that is a Farm Trail listing (Phase 2 compiled data)."""
    r = listings.get(name)
    if not r:
        raise SystemExit(f"plans.json: no Phase 2 listing named {name!r}")
    city = r["City"].strip().title()
    _, tlat, tlng = TOWNS.get(city, (None, None, None))
    try:
        lat, lng, approx = float(r["Latitude"]), float(r["Longitude"]), False
    except ValueError:
        lat, lng, approx = tlat, tlng, True   # no geocode yet: pin the town centre
    return {
        "name": r["Business Name"], "city": city, "kind": r["Category"].split(",")[0].strip(),
        "address": r["Address"], "hours": r["Hours"], "website": r["Website"], "phone": r["Phone"],
        "lat": lat, "lng": lng, "approx": approx,
    }


def resolve_place(ref, ids, by_id, listings, events):
    if "node" in ref:
        nid = ids.get(ref["node"])
        if not nid:
            raise SystemExit(f"plans.json: no supply-network node named {ref['node']!r}")
        return {"node": nid}
    if "listing" in ref:
        p = listing_place(ref["listing"], listings)
        # Prefer the guide page when the listing is also in the supply network.
        nid = ids.get(ref["listing"])
        if nid:
            p["node"] = nid
        return p
    if "event" in ref:
        eid = slug(ref["event"])
        if eid not in {e["id"] for e in events}:
            raise SystemExit(f"plans.json: no event named {ref['event']!r}")
        return {"event": eid}
    raise SystemExit(f"plans.json: stop needs node, listing or event: {ref}")


def load_plans(ids, by_id, events):
    if not PLANS.exists():
        return []
    listings = {r["Business Name"]: r for r in csv.DictReader(open(LISTINGS, encoding="utf-8-sig"))}
    # Rock Bottom's listing name carries "(ACES)"; the network calls it Rock Bottom Ranch.
    alias = {"Rock Bottom Ranch (ACES)": "Rock Bottom Ranch", "Two Roots Farm LLC": "Two Roots Farm"}
    ids = dict(ids, **{k: ids[v] for k, v in alias.items() if v in ids})
    plans = json.load(open(PLANS, encoding="utf-8"))
    for pl in plans:
        for st in pl["stops"]:
            st["place"] = resolve_place(st.pop("place") if "place" in st else st, ids, by_id, listings, events)
            for a in st.get("alt", []):
                a["place"] = resolve_place(a["place"] if "place" in a else a, ids, by_id, listings, events)
                a.pop("event", None)
        if pl.get("pantry"):
            pl["pantry"]["places"] = [resolve_place(r, ids, by_id, listings, events) for r in pl["pantry"]["places"]]
    return plans


def main():
    nodes = list(csv.DictReader(open(NET / "nodes.csv", encoding="utf-8-sig")))
    edges = list(csv.DictReader(open(NET / "edges.csv", encoding="utf-8-sig")))
    trail = {m["name"]: m for m in json.load(open(ROOT / "data" / "markets.json", encoding="utf-8"))}

    out_nodes, ids, unknown_towns = [], {}, set()
    for n in nodes:
        nid = slug(n["name"])
        ids[n["name"]] = nid
        city = n["city"].strip()
        region, lat, lng = TOWNS.get(city, (None, None, None))
        if city in STATEWIDE:
            region = "Statewide"
        elif region is None:
            unknown_towns.add(city)
            region = "Statewide"
        rec = {
            "id": nid, "name": n["name"], "type": n["type"], "city": city,
            "region": region, "lat": lat, "lng": lng, "sup": [], "buy": [],
        }
        t = trail.get(n["on_trail"]) if n["trail_match"] == "exact" else None
        if t:
            rec["trail"] = {k: t.get(k) for k in
                            ("category", "address", "website", "hours", "monthsOpen", "products", "lat", "lng")}
            if t.get("lat"):
                rec["lat"], rec["lng"] = t["lat"], t["lng"]
        out_nodes.append(rec)

    by_id = {r["id"]: r for r in out_nodes}
    out_edges = []
    for e in edges:
        s, b = ids.get(e["supplier"]), ids.get(e["buyer"])
        if not s or not b:
            continue
        ed = {"s": s, "b": b, "c": e["confidence"], "y": year(e["date"]),
              "src": e["source"], "note": e["note"]}
        S, B = by_id[s], by_id[b]
        if S["lat"] and B["lat"]:
            ed["mi"] = round(miles((S["lat"], S["lng"]), (B["lat"], B["lng"])))
        out_edges.append(ed)
        S["buy"].append(len(out_edges) - 1)
        B["sup"].append(len(out_edges) - 1)

    stats = {
        "businesses": len(out_nodes), "links": len(out_edges),
        "high": sum(e["c"] == "high" for e in out_edges),
        "producers": sum(n["type"] in ("farm", "maker") for n in out_nodes),
        "restaurants": sum(n["type"] == "restaurant" for n in out_nodes),
        "shops": sum(n["type"] == "retail" for n in out_nodes),
        "towns": len({n["city"] for n in out_nodes if n["lat"]}),
        "researched": "2026-10-03",
    }
    events = load_events()
    plans = load_plans(ids, by_id, events)
    data = {"nodes": out_nodes, "edges": out_edges, "stats": stats, "typeLabel": TYPE_LABEL,
            "events": events, "plans": plans}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.GUIDE_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {stats}; {len(events)} events, {len(plans)} plans")
    if unknown_towns:
        print("towns without coordinates (filed under Statewide):", sorted(unknown_towns))


if __name__ == "__main__":
    main()
