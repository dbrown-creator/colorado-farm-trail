#!/usr/bin/env python3
"""Re-pull the Colorado Proud Farm Fresh Directory from ArcGIS and rebuild both CSVs.

Source: the public ArcGIS Feature Service behind the map on
https://coloradoproud.com/find-farm-fresh-favorites/ (see DATA.md for how it was traced).

Outputs (into ../data/):
  - colorado_proud_farm_fresh_directory_raw.csv : all 47 fields + Latitude/Longitude
  - farm_fresh_directory_mymaps.csv             : cleaned, Google My Maps import-ready

Usage:
  python scripts/fetch_farm_data.py
"""
import csv
import json
import os
import urllib.request

FS = ("https://services3.arcgis.com/DgjqnJA1rgO92Soi/arcgis/rest/services/"
      "Farm_Fresh_Directory/FeatureServer/0/query")
QUERY = "?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=json"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")

# priority-ordered buckets -> single Category for map styling
PRIORITY = [
    ("Winery", "Winery"), ("U-pick", "U-Pick"), ("Farmers' Market", "Farmers' Market"),
    ("CSA", "CSA Farm"), ("Roadside Market", "Roadside Market"),
    ("Greenhouse", "Garden Center / Greenhouse"), ("Garden Center", "Garden Center / Greenhouse"),
    ("Agritourism", "Agritourism"), ("Restaurant", "Restaurant"),
    ("On-Farm", "On-Farm / Ranch Sales"), ("Ranch", "On-Farm / Ranch Sales"),
    ("Sell to Schools", "Sells to Schools"),
]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
PROD_FIELDS = [
    "Produce Categories 1", "Produce Categories 2", "Produce Categories 3",
    "Produce Categories (other)", "Meat Categories", "Game", "Fish", "Meat (other)",
    "Miscellaneous 1", "Miscellaneous 2", "Miscellaneous (Other)", "Wines",
]


def pipes(s):
    return ", ".join(p.strip() for p in (s or "").split("|") if p.strip())


def category(op):
    op = op or ""
    for key, label in PRIORITY:
        if key.lower() in op.lower():
            return label
    return "Other"


def fetch():
    req = urllib.request.Request(FS + QUERY, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def write_raw(d, path):
    fields = [f for f in d["fields"] if f["name"] != "ObjectID"]
    names = [f["name"] for f in fields]
    alias = {f["name"]: f.get("alias", f["name"]) for f in fields}
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow([alias[n] for n in names] + ["Latitude", "Longitude"])
        for ft in d["features"]:
            a = ft.get("attributes", {})
            g = ft.get("geometry") or {}
            w.writerow([a.get(n, "") for n in names] + [g.get("y", ""), g.get("x", "")])


def a(ft, alias_to_name, alias):
    """Get an attribute by its alias label."""
    return (ft["attributes"].get(alias_to_name.get(alias, ""), "") or "").strip()


def write_mymaps(d, path):
    # map alias -> raw field name so we can read by human label
    alias_to_name = {f.get("alias", f["name"]): f["name"] for f in d["fields"]}

    def get(ft, label):
        return (ft["attributes"].get(alias_to_name.get(label, ""), "") or "").strip()

    def addr(ft):
        line1 = get(ft, "Address Line 1")
        line2 = get(ft, "Address Line 2")
        return (line1 + " " + line2).strip() if line2 else line1

    def hours(ft):
        parts = [f"{day[:3]}: {get(ft, 'Hours on ' + day)}"
                 for day in DAYS if get(ft, "Hours on " + day)]
        return "; ".join(parts)

    def products(ft):
        vals = [pipes(get(ft, f)) for f in PROD_FIELDS]
        return ", ".join(v for v in vals if v)

    cols = ["Business Name", "Category", "Address", "City", "County", "State", "Zip",
            "Phone", "Call first?", "Website", "Email", "Facebook", "Instagram",
            "Hours", "Months Open", "Products", "Certified Organic", "SNAP",
            "ADA Accessible", "Notes", "Latitude", "Longitude"]

    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for ft in d["features"]:
            g = ft.get("geometry") or {}
            w.writerow({
                "Business Name": get(ft, "Business Name"),
                "Category": category(get(ft, "Operation type")),
                "Address": addr(ft), "City": get(ft, "City"), "County": get(ft, "County"),
                "State": get(ft, "State"), "Zip": get(ft, "Zip"),
                "Phone": get(ft, "Telephone Number"),
                "Call first?": get(ft, "Should the customer call first?"),
                "Website": get(ft, "Website"), "Email": get(ft, "Email Address"),
                "Facebook": get(ft, "Facebook"), "Instagram": get(ft, "Instagram"),
                "Hours": hours(ft), "Months Open": pipes(get(ft, "Months open for business")),
                "Products": products(ft),
                "Certified Organic": get(ft, "Certified organic"),
                "SNAP": get(ft, "SNAP accepted"),
                "ADA Accessible": get(ft, "ADA accessible"),
                "Notes": get(ft, "Additional information"),
                "Latitude": g.get("y", ""), "Longitude": g.get("x", ""),
            })


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    d = fetch()
    n = len(d["features"])
    write_raw(d, os.path.join(DATA_DIR, "colorado_proud_farm_fresh_directory_raw.csv"))
    write_mymaps(d, os.path.join(DATA_DIR, "farm_fresh_directory_mymaps.csv"))
    print(f"Pulled {n} farms. Rebuilt both CSVs in {os.path.normpath(DATA_DIR)}.")


if __name__ == "__main__":
    main()
