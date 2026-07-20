"""Source: USDA Local Food Portal — National Farmers Market Directory.

Two endpoints:

  * data_share (NO key)  -> /mywp/wp-json/frontend/data_share?directory=farmersmarket&state=co
    Only returns listings that opted into data-sharing (≈6 CO markets) and a thin
    field set. Useful as a cross-check only.

  * api (KEY required)   -> /api/farmersmarket/?apikey=KEY&x=LON&y=LAT&radius=MILES
    The full directory near a point, with the rich field set (lat/lon, season, hours,
    products, payment/SNAP, social). This is the statewide backbone once the key
    lands. We sweep a grid of points across Colorado and dedupe by listing id.

Field names below follow the portal's documented JSON. Because we don't yet have a
live keyed sample, `parse_api` is written defensively (every field guarded) and is
covered by a fixture-based test; verify against a real response when the key arrives.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import List

from ..normalize import clean_url, phone, titlecase, zipcode
from ..schema import Market

DATASHARE = "https://www.usdalocalfoodportal.com/mywp/wp-json/frontend/data_share"
API = "https://www.usdalocalfoodportal.com/api/farmersmarket/"
SOURCE = "usda"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# A coarse grid of points (lon, lat) covering Colorado; each queried with a radius
# wide enough to overlap its neighbors, so no market is missed. Deduped by id.
CO_GRID = [
    (lon, lat)
    for lat in (37.4, 38.4, 39.4, 40.4)
    for lon in (-108.2, -106.2, -104.2, -102.6)
]
GRID_RADIUS_MILES = 60


def _get_json(url: str, timeout: int = 40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ---- keyless data_share (thin) ------------------------------------------------

def fetch_datashare_raw(state: str = "co") -> list:
    q = urllib.parse.urlencode({"directory": "farmersmarket", "state": state})
    return _get_json(f"{DATASHARE}?{q}")


def parse_datashare(rows: list) -> List[Market]:
    out = []
    for r in rows:
        m = Market(source=SOURCE)
        m.set("business_name", r.get("Listing_Name", ""), SOURCE)
        m.set("address", r.get("Location_Street", ""), SOURCE)
        m.set("city", r.get("Location_City", ""), SOURCE)
        m.set("zip", zipcode(r.get("Location_Zipcode", "")), SOURCE)
        m.set("phone", phone(r.get("Contact_Phone", "")), SOURCE)
        m.set("email", r.get("Contact_Email", ""), SOURCE)
        m.set("website", clean_url(r.get("Media_Website", "")), SOURCE)
        if m.business_name:
            out.append(m)
    return out


# ---- keyed API (rich) ---------------------------------------------------------

def fetch_api_raw(apikey: str, lon: float, lat: float, radius: int = GRID_RADIUS_MILES):
    q = urllib.parse.urlencode({"apikey": apikey, "x": lon, "y": lat, "radius": radius})
    return _get_json(f"{API}?{q}")


def _api_records(payload) -> list:
    """The portal has returned either a bare list or {'data': [...]}; handle both."""
    if isinstance(payload, dict):
        return payload.get("data") or payload.get("results") or []
    return payload or []


def _s(r, key):
    """Portal uses null and '' interchangeably; return a clean string."""
    v = r.get(key)
    return "" if v is None else str(v).strip()


def parse_api(payload) -> List[Market]:
    """Map a real keyed-API response. Verified against a live CO sample: the farmers
    market API carries identity/location/contact/social only — NO hours, season,
    products, SNAP, organic, or county. Those stay empty here (filled by Colorado
    Proud or later per-site enrichment). County/coords-gap handled by the geocoder."""
    out = []
    for r in _api_records(payload):
        state = _s(r, "location_state").lower()
        if state and state not in ("colorado", "co"):
            continue  # grid edges can pull neighboring states
        m = Market(source=SOURCE)
        m.set("business_name", _s(r, "listing_name"), SOURCE)
        m.set("address", titlecase(_s(r, "location_street")), SOURCE)
        m.set("city", titlecase(_s(r, "location_city")), SOURCE)
        m.set("zip", zipcode(_s(r, "location_zipcode")), SOURCE)
        m.set("phone", phone(_s(r, "contact_phone")), SOURCE)
        m.set("email", _s(r, "contact_email"), SOURCE)
        m.set("website", clean_url(_s(r, "media_website")), SOURCE)
        m.set("facebook", clean_url(_s(r, "media_facebook")), SOURCE)
        m.set("instagram", clean_url(_s(r, "media_instagram")), SOURCE)
        m.set("notes", _s(r, "listing_desc") or _s(r, "brief_desc"), SOURCE)
        lon, lat = _s(r, "location_x"), _s(r, "location_y")
        try:
            if lon and lat:
                m.longitude, m.latitude = float(lon), float(lat)
                m.geo_source = "source"
        except (TypeError, ValueError):
            pass
        if m.business_name:
            out.append(m)
    return out


def fetch_api(apikey: str) -> List[Market]:
    """Sweep the CO grid, dedupe by (name, city)."""
    seen, out = set(), []
    for lon, lat in CO_GRID:
        try:
            payload = fetch_api_raw(apikey, lon, lat)
        except Exception:
            continue
        for m in parse_api(payload):
            key = (m.business_name.lower(), m.city.lower())
            if key not in seen:
                seen.add(key)
                out.append(m)
    return out
