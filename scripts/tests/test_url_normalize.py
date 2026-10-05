"""Offline tests for the shared Website / Facebook / Instagram URL normalization.

The rules live in scrape/normalize.py and are used by both the Phase 2 scraper
sources and the live Phase 1 build (build_map_data.py). Run:
python -m pytest scripts/tests -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_map_data
from scrape import normalize as N
from scrape.sources import enrichment


@pytest.mark.parametrize("raw,exp", [
    # bare handles (Instagram allows dots)
    ("cbfarmersmarket", "https://instagram.com/cbfarmersmarket"),
    ("abundant.spaces", "https://instagram.com/abundant.spaces"),
    # '@' handles
    ("@durangofarmers", "https://instagram.com/durangofarmers"),
    ("@durangofarmers/", "https://instagram.com/durangofarmers"),
    # scheme-less URLs
    ("www.instagram.com/pueblofarmersmarket", "https://www.instagram.com/pueblofarmersmarket"),
    ("instagram.com/x", "https://instagram.com/x"),
    # already a URL; uppercase scheme is lowercased, host case kept
    ("https://www.instagram.com/x/", "https://www.instagram.com/x/"),
    ("Http://Instagram.com/X", "http://Instagram.com/X"),
    # page names / junk -> ''
    ("Durango Farmers Market", ""),
    ("Bob's & Co", ""),
    ("linktr.ee/foo", ""),
    ("", ""),
    (None, ""),
])
def test_instagram_url(raw, exp):
    assert N.instagram_url(raw) == exp


@pytest.mark.parametrize("raw,exp", [
    ("www.facebook.com/townofmountainvillage", "https://www.facebook.com/townofmountainvillage"),
    ("m.facebook.com/x", "https://m.facebook.com/x"),
    ("fb.com/x", "https://fb.com/x"),
    ("@gunnisonfm", "https://facebook.com/gunnisonfm"),
    ("gunnisonfm", "https://facebook.com/gunnisonfm"),
    ("HTTPS://www.facebook.com/x", "https://www.facebook.com/x"),
    ("Gunnison Farmers Market", ""),
    ("Foodshed Alliance", ""),
    ("@a, @b", "https://facebook.com/a"),
    ("  ", ""),
])
def test_facebook_url(raw, exp):
    assert N.facebook_url(raw) == exp


@pytest.mark.parametrize("raw,exp", [
    ("littletonq.com", "https://littletonq.com"),
    ("www.salidacattlecompany.com", "https://www.salidacattlecompany.com"),
    ("https://x.com", "https://x.com"),
    ("Http://www.salidacattlecompany.com", "http://www.salidacattlecompany.com"),
    ("HTTPS://Example.com/Path", "https://Example.com/Path"),
    # multi-value cells keep the first usable URL
    ("www.yakmeat.us  , www.yaksale.com", "https://www.yakmeat.us"),
    ("Yak Ranch; yaksale.com", "https://yaksale.com"),
    ("https://x.com/?a=1,2", "https://x.com/?a=1,2"),
    ("Salida Cattle Company", ""),
    ("Some Name.com", ""),
    ("N/A", ""),
    ("none", ""),
    ("-", ""),
    ("", ""),
])
def test_clean_url(raw, exp):
    assert N.clean_url(raw) == exp


def test_phase1_build_uses_shared_helpers():
    # One copy of the rules: the live build imports them rather than redefining them.
    assert build_map_data.website_url is N.website_url
    assert build_map_data.social_url is N.social_url
    assert build_map_data.social_url("Foodshed Alliance", N.FACEBOOK_BASE) is None


def test_enrichment_normalizes_social_fields():
    results = [{"id": "t1", "fields": {
        "Website": "Http://www.salidacattlecompany.com",
        "Facebook": {"value": "Foodshed Alliance"},
        "Instagram": {"value": "@durangofarmers"},
    }}]
    targets = {"t1": {"name": "Test Market", "city": "Durango"}}
    m = enrichment.parse(results, targets)[0]
    assert m.website == "http://www.salidacattlecompany.com"
    assert m.facebook == ""
    assert m.instagram == "https://instagram.com/durangofarmers"


def test_fix_mojibake_repairs_cp1252_misreads():
    from scrape.normalize import fix_mojibake
    assert fix_mojibake("Salidaâ€™s Farmers Market") == "Salida’s Farmers Market"
    assert fix_mojibake("CaÃ±on City") == "Cañon City"
    assert fix_mojibake("Mayâ€“October") == "May–October"
    assert fix_mojibake("A familyâ€‘run ranch") == "A family‑run ranch"
    assert fix_mojibake("white, rosÃ©, and sparkling") == "white, rosé, and sparkling"
    # Clean text, including real accents and dashes, is left alone.
    for s in ("Cañon City", "Farmers' Market", "May–October", "Café", ""):
        assert fix_mojibake(s) == s
