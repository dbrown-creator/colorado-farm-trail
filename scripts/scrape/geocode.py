"""Free, key-less geocoding + county lookup.

Two public services, both no-key and generous for our volume (~150 rows):

  * US Census Geocoder  -> forward geocode an address to lat/lon *and* county.
    https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress
  * FCC Area API        -> reverse lookup a county name from lat/lon (for records
    that already have coordinates from their source but no county).
    https://geo.fcc.gov/api/census/block/find

Every coordinate produced here is tagged geo_source='census-geocoder' so the map/raw
CSV can distinguish source-provided pins from derived ones (the geocode+flag rule).
Network calls are isolated behind tiny functions so tests can monkeypatch them.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Optional, Tuple

UA = {"User-Agent": "ColoradoFarmTrail/1.0 (+https://github.com) data build"}
CENSUS = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
FCC = "https://geo.fcc.gov/api/census/block/find"


def _get_json(url: str, timeout: int = 30) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def geocode_address(address: str, city: str, zipc: str) -> Optional[Tuple[float, float, str]]:
    """Forward-geocode 'address, city, CO zip'. Returns (lat, lon, county) or None.

    County comes back from the same call (Census geographies layer), so a single
    request fills both the coordinates and the County column at high confidence."""
    line = ", ".join(p for p in [address, city, "CO", zipc] if p)
    if not address or not city:
        return None
    q = urllib.parse.urlencode({
        "address": line, "benchmark": "Public_AR_Current",
        "vintage": "Current_Current", "format": "json",
    })
    data = _get_json(f"{CENSUS}?{q}")
    try:
        matches = data["result"]["addressMatches"]
        if not matches:
            return None
        m = matches[0]
        lat = float(m["coordinates"]["y"])
        lon = float(m["coordinates"]["x"])
        county = ""
        counties = m.get("geographies", {}).get("Counties", [])
        if counties:
            county = counties[0].get("NAME", "").replace(" County", "").strip()
        return lat, lon, county
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def county_for(lat: float, lon: float) -> str:
    """Reverse lookup: county name for a lat/lon (no key). '' on failure."""
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "format": "json"})
    data = _get_json(f"{FCC}?{q}")
    try:
        name = (data.get("County", {}).get("name") or "").strip()
        return re.sub(r"\s+County$", "", name)
    except AttributeError:
        return ""
