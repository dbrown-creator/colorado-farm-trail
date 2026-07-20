"""Source: Colorado Farmers Market Association member markets.

The `cofarmersmarkets.org` "Find a Market" map is a MarketWurks embed; its data is a
public REST API keyed by CFMA's org id (found in the homepage embed's `data-org-id`).
No key/login needed — just the X-Account-ID header. See scripts/scrape/README.md.

CFMA members carry exactly the fields USDA lacks (hours, season, social, SNAP via
"Programs", description, precise coords), so this is a high-value enrichment + a source
of ~11 markets absent from the directories. Multichoice codes (day/month/programs) are
decoded from the live signup-form definition rather than hardcoded, so the mapping
stays correct if CFMA reorders options.
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import List

from ..normalize import clean_url, zipcode
from ..schema import Market

# CFMA org id, read from the homepage MarketWurks embed (data-org-id). Stable per-tenant.
ORG_ID = "b33b989cea991edcf0db27887992a281"
BASE = "https://app.marketwurks.com"
SOURCE = "cfma"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "X-Account-ID": ORG_ID}

DAY_ABBR = {
    "Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu",
    "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun",
}


def _get(path: str):
    req = urllib.request.Request(BASE + path, headers=HDR)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_form():
    return _get("/api/forms/signup")


def fetch_vendors():
    return _get("/api/vendors/activeWithFields")


def option_maps(form) -> dict:
    """Build {field name -> {code: label}} for every MultichoiceElement in the form."""
    maps: dict = {}

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "MultichoiceElement" and x.get("options"):
                maps[(x.get("name") or "").strip()] = {
                    o["id"]: (o.get("name") or "").strip() for o in x["options"]
                }
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(form)
    return maps


def _split_address(text: str):
    """'816 Royal Gorge Blvd, Cañon City, CO 81212, USA' -> (street, city, zip)."""
    parts = [p.strip() for p in (text or "").split(",") if p.strip()]
    zc = zipcode(text)
    # find the 'CO 81212' (state+zip) part; city is the part just before it
    state_idx = next(
        (i for i, p in enumerate(parts) if re.match(r"^[A-Z]{2}\b", p) and zipcode(p)),
        None,
    )
    if state_idx and state_idx >= 1:
        city = parts[state_idx - 1]
        street = ", ".join(parts[: state_idx - 1])
    else:  # fallback: assume [street, city, ...]
        street = parts[0] if parts else ""
        city = parts[1] if len(parts) > 1 else ""
    return street, city, zc


def _instagram(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    if v.startswith("http"):
        return clean_url(v)
    handle = v.lstrip("@").strip().rstrip("/")
    handle = re.sub(r"\.com$", "", handle)  # some values are '@name.com' typos
    return f"https://www.instagram.com/{handle}" if handle else ""


def _hours(days: List[str], opens: str, closes: str) -> str:
    opens, closes = (opens or "").strip(), (closes or "").strip()
    time = f"{opens} - {closes}" if opens and closes else (opens or closes)
    if not days:
        return ""
    if not time:
        return ", ".join(DAY_ABBR.get(d, d) for d in days)
    return "; ".join(f"{DAY_ABBR.get(d, d)}: {time}" for d in days)


def parse(vendors, form) -> List[Market]:
    opt = option_maps(form)
    days_map = opt.get("Market Day(s)", {})
    months_map = opt.get("Months Open", {})
    prog_map = opt.get("Programs", {})

    out: List[Market] = []
    for v in vendors.get("vendors", []):
        f = {(fld.get("name") or "").strip(): fld.get("value") for fld in v.get("fields", [])}
        m = Market(source=SOURCE)
        m.set("business_name", f.get("Market name"), SOURCE)

        loc = f.get("Market Location")
        if isinstance(loc, dict):
            street, city, zc = _split_address(loc.get("textName", ""))
            m.set("address", street, SOURCE)
            m.set("city", city, SOURCE)
            m.set("zip", zc, SOURCE)
            try:
                if loc.get("latitude") and loc.get("longitude"):
                    m.latitude = float(loc["latitude"])
                    m.longitude = float(loc["longitude"])
                    m.geo_source = "source"
            except (TypeError, ValueError):
                pass

        m.set("website", clean_url(f.get("Website")), SOURCE)
        m.set("facebook", clean_url(f.get("Facebook")), SOURCE)
        m.set("instagram", _instagram(f.get("Instagram")), SOURCE)

        days = [days_map.get(c, c) for c in (f.get("Market Day(s)") or [])]
        m.set("hours", _hours(days, f.get("Market Opens"), f.get("Market Closes")), SOURCE)

        months = [months_map.get(c, c) for c in (f.get("Months Open") or [])]
        m.set("months_open", ", ".join(months), SOURCE)

        progs = [prog_map.get(c, c) for c in (f.get("Programs") or [])]
        if any("snap" in p.lower() for p in progs):
            m.set("snap", "Yes", SOURCE)

        desc = (f.get("Market Description") or "").strip()
        extras = []
        if progs:
            extras.append("Programs: " + ", ".join(progs))
        starts, ends = f.get("Market Starts"), f.get("Market Ends")
        if starts and ends:
            extras.append(f"Season {starts}–{ends}")
        note = " | ".join([p for p in [desc, "; ".join(extras)] if p])
        m.set("notes", note, SOURCE)

        if m.business_name:
            out.append(m)
    return out


def fetch() -> List[Market]:
    return parse(fetch_vendors(), fetch_form())
