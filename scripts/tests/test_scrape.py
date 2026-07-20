"""Offline tests for the Colorado farmers-market scraper.

No network: source parsers are exercised against saved fixtures, geocoding is
monkeypatched. Run:  python -m pytest scripts/tests -q
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrape import merge as merge_mod
from scrape import normalize as N
from scrape.schema import Market
from scrape.sources import cfma, usda

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


# ---- normalize helpers --------------------------------------------------------

@pytest.mark.parametrize("raw,exp", [
    ("7197786041", "(719) 778-6041"),
    ("(970)549-7151", "(970) 549-7151"),
    ("1-720-254-1534", "(720) 254-1534"),
    ("555", ""),
    ("", ""),
])
def test_phone(raw, exp):
    assert N.phone(raw) == exp


@pytest.mark.parametrize("raw,exp", [
    ("81003", "81003"), ("80202-1234", "80202"), ("Denver CO 80014", "80014"), ("", "")
])
def test_zip(raw, exp):
    assert N.zipcode(raw) == exp


def test_name_key_matches_apostrophe_variants():
    assert N.name_key("Pueblo Farmers Market") == N.name_key("Pueblo Farmers' Market")
    assert N.name_key("Downtown Boulder Farmers Market") == N.name_key("Boulder Farmers Market")


def test_clean_url():
    assert N.clean_url("littletonq.com") == "https://littletonq.com"
    assert N.clean_url("https://x.com") == "https://x.com"
    assert N.clean_url("N/A") == ""


def test_in_colorado():
    assert N.in_colorado(39.75, -105.0)      # Denver
    assert not N.in_colorado(40.71, -74.0)   # NYC
    assert not N.in_colorado(None, None)


# ---- USDA data_share mapping (real fixture) -----------------------------------

def test_datashare_parses_fixture():
    rows = json.load(open(os.path.join(FIX, "usda_datashare_farmersmarket_co.json")))
    markets = usda.parse_datashare(rows)
    assert len(markets) == 6
    pueblo = next(m for m in markets if "Pueblo" in m.business_name)
    assert pueblo.city == "Pueblo"
    assert pueblo.zip == "81003"
    assert pueblo.phone == "(719) 778-6041"
    assert pueblo.provenance["Phone"] == "usda"


# ---- USDA keyed API mapping (synthetic fixture until a real key exists) --------

def test_api_parse_real_fixture():
    """Against a live CO sample: identity/location/contact/social map through;
    city/street get title-cased; hours/season/products/SNAP are absent by design."""
    payload = json.load(open(os.path.join(FIX, "usda_api_sample.json")))
    markets = usda.parse_api(payload)
    assert markets, "fixture should yield markets"
    m = next(x for x in markets if "Tiri" in x.business_name)
    assert m.city == "Denver"                       # was 'DENVER'
    assert m.address == "1522 California St"         # was '1522 CALIFORNIA ST'
    assert m.zip == "80202"
    assert m.phone == "(303) 605-2885"
    assert m.latitude == pytest.approx(39.7444, abs=1e-3) and m.geo_source == "source"
    # documents the API's thinness: these never come from USDA
    assert m.hours == "" and m.months_open == "" and m.products == "" and m.snap == ""


def test_api_filters_non_colorado():
    payload = [
        {"listing_name": "CO Market", "location_state": "Colorado",
         "location_city": "Denver", "location_x": "-105", "location_y": "39.7"},
        {"listing_name": "Kansas Market", "location_state": "Kansas",
         "location_city": "Goodland", "location_x": "-101.7", "location_y": "39.35"},
    ]
    names = [m.business_name for m in usda.parse_api(payload)]
    assert names == ["CO Market"]


# ---- CFMA / MarketWurks mapping (real fixtures) -------------------------------

def test_cfma_parses_and_decodes_fields():
    vendors = json.load(open(os.path.join(FIX, "cfma_marketwurks_activeWithFields_sample.json"), encoding="utf-8"))
    form = json.load(open(os.path.join(FIX, "cfma_marketwurks_signupform_sample.json"), encoding="utf-8"))
    markets = cfma.parse(vendors, form)
    assert len(markets) == 37
    wp = next(m for m in markets if "Woodland Park" in m.business_name)
    # the key decode: Market Day(s) is 0-indexed Monday, so code 4 == Friday
    assert "Fri:" in wp.hours
    assert wp.city == "Woodland Park" and wp.zip == "80863"
    assert wp.latitude and wp.longitude and wp.geo_source == "source"
    assert "June" in wp.months_open
    # Programs -> SNAP; Woodland Park offers SNAP (code 0)
    assert wp.snap == "Yes"


def test_cfma_instagram_and_address_helpers():
    assert cfma._instagram("@downtownglenwoodsprings") == "https://www.instagram.com/downtownglenwoodsprings"
    assert cfma._instagram("https://instagram.com/x") == "https://instagram.com/x"
    street, city, zc = cfma._split_address("816 Royal Gorge Blvd, Cañon City, CO 81212, USA")
    assert street == "816 Royal Gorge Blvd" and city == "Cañon City" and zc == "81212"


# ---- dedup / merge ------------------------------------------------------------

def _mk(name, city, source, **kw):
    m = Market(source=source)
    m.set("business_name", name, source)
    m.set("city", city, source)
    for k, v in kw.items():
        m.set(k, v, source)
    return m


def test_merge_collapses_overlap_and_fills_gaps():
    # Same market from two sources; Colorado Proud first (wins), USDA fills email.
    cp = _mk("Pueblo Farmers' Market", "Pueblo", "colorado_proud",
             phone="(719) 778-6041", website="https://a.org")
    us = _mk("Pueblo Farmers Market", "Pueblo", "usda",
             email="x@y.org", website="https://b.org")
    out = merge_mod.merge([cp, us])
    assert len(out) == 1
    row = out[0]
    assert row.website == "https://a.org"          # first source wins
    assert row.email == "x@y.org"                   # gap filled from usda
    assert row.provenance["Email"] == "usda"
    assert "colorado_proud" in row.source and "usda" in row.source


def test_merge_keeps_distinct_markets():
    a = _mk("Boulder Farmers Market", "Boulder", "usda")
    b = _mk("Longmont Farmers Market", "Longmont", "usda")
    assert len(merge_mod.merge([a, b])) == 2


def test_flag_possible_dups_name_subset_only():
    a = _mk("Evergreen Farmers Market", "Evergreen", "usda")
    b = _mk("Evergreen Farmers Market THE ORIGINAL", "Evergreen", "colorado_proud")
    # distinct East/West markets share a stem but neither name is a subset -> no flag
    c = _mk("Loveland East Market", "Loveland", "usda")
    d = _mk("Loveland West Market", "Loveland", "usda")
    ms = [a, b, c, d]
    merge_mod.flag_possible_dups(ms)
    assert a.dup_hint and b.dup_hint            # subset match flagged
    assert not c.dup_hint and not d.dup_hint    # East vs West kept clean


def test_merge_by_coordinate_proximity():
    a = _mk("Old Town Market", "Fort Collins", "colorado_proud")
    a.latitude, a.longitude = 40.5853, -105.0844
    b = _mk("Old Town Farmers Mkt", "Fort Collins", "usda")  # name drift, ~50m away
    b.latitude, b.longitude = 40.5857, -105.0844
    assert len(merge_mod.merge([a, b])) == 1
