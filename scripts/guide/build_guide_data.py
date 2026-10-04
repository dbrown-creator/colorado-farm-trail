"""Build guide/guide-data.js for the local food guide draft.

Reads the supply-network pilot (source-data/supply-network/{nodes,edges}.csv)
and the farm-trail listings (data/markets.json), and writes one JS file the
static guide loads. Town coordinates are town centroids, so per-business
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
    "Silt": ("Roaring Fork", 39.5486, -107.6562),
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
    "Meeker": ("Northwest", 40.0375, -107.9131), "Hayden": ("Northwest", 40.4953, -107.2573),
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
        # sup/buy hold current links; supOld/buyOld hold older mentions a re-check couldn't confirm.
        rec = {
            "id": nid, "name": n["name"], "type": n["type"], "city": city,
            "region": region, "lat": lat, "lng": lng, "sup": [], "buy": [], "supOld": [], "buyOld": [],
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
        old = e.get("status") == "unconfirmed"
        ed = {"s": s, "b": b, "c": e["confidence"], "y": year(e["date"]),
              "src": e["source"], "note": e["note"]}
        if old:
            ed["old"] = 1
        S, B = by_id[s], by_id[b]
        if S["lat"] and B["lat"]:
            ed["mi"] = round(miles((S["lat"], S["lng"]), (B["lat"], B["lng"])))
        out_edges.append(ed)
        S["buyOld" if old else "buy"].append(len(out_edges) - 1)
        B["supOld" if old else "sup"].append(len(out_edges) - 1)

    # Businesses with no links left (e.g. every link retired after a re-check) drop out of the guide.
    linked = [r for r in out_nodes if r["sup"] or r["buy"] or r["supOld"] or r["buyOld"]]
    remap = {r["id"]: r for r in linked}
    if len(linked) != len(out_nodes):
        print("dropped unlinked:", sorted(r["name"] for r in out_nodes if r["id"] not in remap))
    out_nodes = linked

    current = [e for e in out_edges if not e.get("old")]
    stats = {
        "businesses": len(out_nodes), "links": len(current), "older": len(out_edges) - len(current),
        "high": sum(e["c"] == "high" for e in current),
        "producers": sum(n["type"] in ("farm", "maker") for n in out_nodes),
        "restaurants": sum(n["type"] == "restaurant" for n in out_nodes),
        "shops": sum(n["type"] == "retail" for n in out_nodes),
        "towns": len({n["city"] for n in out_nodes if n["lat"]}),
        "researched": "2026-10-03", "rechecked": "2026-10-04",
    }
    data = {"nodes": out_nodes, "edges": out_edges, "stats": stats, "typeLabel": TYPE_LABEL}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.GUIDE_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {stats}")
    if unknown_towns:
        print("towns without coordinates (filed under Statewide):", sorted(unknown_towns))


if __name__ == "__main__":
    main()
