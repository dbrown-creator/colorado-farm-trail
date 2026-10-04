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


# ---- USDA data_share: the four non-farmersmarket directories ------------------

@pytest.mark.parametrize("directory,name,category", [
    ("onfarmmarket", "RK Creations Farm", "On-Farm / Ranch Sales"),
    ("csa", "Two Roots Farm", "CSA Farm"),
    ("foodhub", "Food to Power", "Food Hub"),
    ("agritourism", "Colorado Aromatics", "Agritourism"),
])
def test_datashare_other_directories(directory, name, category):
    fix = json.load(open(os.path.join(FIX, "usda_datashare_directories_co_sample.json")))
    markets = usda.parse_datashare(fix[directory], directory)
    m = next(x for x in markets if x.business_name == name)
    assert m.category == category
    assert m.state == "CO"


def test_datashare_handles_messy_values():
    """Real data_share quirks: null street, ' City' with leading space, '80504.0' zip,
    truncated phone ('719-470-27' -> dropped by the 10-digit rule)."""
    fix = json.load(open(os.path.join(FIX, "usda_datashare_directories_co_sample.json")))
    hub = usda.parse_datashare(fix["foodhub"], "foodhub")[0]
    assert hub.city == "Colorado Springs"     # leading space stripped
    assert hub.phone == ""                    # truncated source phone rejected
    agri = usda.parse_datashare(fix["agritourism"], "agritourism")[0]
    assert agri.zip == "80504"                # '80504.0' float-ish zip recovered
    csa = next(m for m in usda.parse_datashare(fix["csa"], "csa")
               if "Sunshine" in m.business_name)
    assert csa.address == ""                  # null street stays empty


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
    # update-engine hooks: stable id + source update stamp captured
    assert m.source_id == "309128"
    assert m.source_updated == "Mar 20th, 2023"
    # category from the record's own directory_type discriminator
    assert m.category == "Farmers' Market"


def test_api_category_from_directory_type():
    """The same parser serves all five directories: directory_type on the record
    wins; the fetched-from directory is the fallback."""
    rec = {"listing_name": "Ute Farmstand", "location_state": "Colorado",
           "location_city": "Olathe", "directory_type": "onfarmmarket"}
    m = usda.parse_api([rec], directory="csa")[0]
    assert m.category == "On-Farm / Ranch Sales"      # record discriminator wins
    m2 = usda.parse_api([{"listing_name": "Veggie Box", "location_state": "Colorado",
                          "location_city": "Denver"}], directory="csa")[0]
    assert m2.category == "CSA Farm"                  # fallback to fetched directory


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


def test_merge_carries_source_id_for_change_detection():
    cp = _mk("Pueblo Farmers' Market", "Pueblo", "colorado_proud")
    us = _mk("Pueblo Farmers Market", "Pueblo", "usda")
    us.source_id, us.source_updated = "309128", "Mar 20th, 2023"
    row = merge_mod.merge([cp, us])[0]
    assert row.source_id == "309128" and row.source_updated == "Mar 20th, 2023"


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


# ---- Chaffee Provides (chaffeeprovides.org) -----------------------------------

from scrape.sources import chaffee_provides as chaffee  # noqa: E402


def _chaffee(name):
    return open(os.path.join(FIX, f"chaffee_{name}.html"), encoding="utf-8").read()


def _chaffee_detail(slug, cats=()):
    return chaffee.parse_detail(_chaffee(f"provider_{slug}"), slug, list(cats))


def test_chaffee_listing_finds_cards_and_pagination():
    slugs, pages = chaffee.parse_listing(_chaffee("list_markets-foodbanks_p1"))
    assert len(slugs) == 12 and len(set(slugs)) == 12
    assert "arkansas-valley-christian-mission" in slugs
    assert any(p.rstrip("/").endswith("/markets-foodbanks/page/2") for p in pages)
    slugs2, _ = chaffee.parse_listing(_chaffee("list_markets-foodbanks_p2"))
    assert len(slugs2) == 5 and not set(slugs) & set(slugs2)


def test_chaffee_crawl_follows_pagination_and_dedupes():
    pages = {
        f"{chaffee.BASE}/product-offerings/markets-foodbanks/": _chaffee("list_markets-foodbanks_p1"),
        f"{chaffee.BASE}/product-offerings/markets-foodbanks/page/2/": _chaffee("list_markets-foodbanks_p2"),
        f"{chaffee.BASE}/product-offerings/beef-meat/": _chaffee("list_beef-meat_p1"),
    }
    fetched = []

    def fake_get(url):
        fetched.append(url)
        return pages.get(url, "<html></html>")

    members = chaffee.crawl_categories(fake_get)
    assert len(fetched) == len(chaffee.CATEGORY_SLUGS) + 1     # one extra: page 2
    listed = set()
    for html in pages.values():
        listed |= set(chaffee.parse_listing(html)[0])
    assert set(members) == listed and len(listed) < 12 + 5 + 10   # overlap fetched once
    assert set(members["valley-roots-food-hub"]) == {"Beef/Meat", "Markets/Food Banks"}


def test_chaffee_detail_maps_fields_with_provenance():
    m = _chaffee_detail("arrowpoint-cattle-company", ["Beef/Meat"])
    assert m.business_name == "Arrowpoint Cattle Company"
    assert m.category == "On-Farm / Ranch Sales"
    assert m.phone == "(303) 618-3135"
    assert m.email == "arrowpointcc@aol.com"
    assert m.website == "https://www.arrowpointcattle.com"
    assert m.products == "Beef/Meat, Poultry/Eggs"     # category page deduped
    assert m.notes.startswith("All natural grass-fed highland beef")
    assert m.source == m.provenance["Phone"] == m.provenance["Products"] == "chaffee_provides"
    assert m.source_id == "arrowpoint-cattle-company"
    assert m.latitude is None                           # left for fill_geography


def test_chaffee_street_only_address_invents_nothing():
    m = _chaffee_detail("arrowpoint-cattle-company")
    assert m.address == "21900 County Road 196"
    assert m.city == "" and m.zip == "" and m.county == ""   # house number is not a zip


def test_chaffee_address_split_when_city_and_zip_stated():
    m = _chaffee_detail("mountain-goat-lodge")
    assert (m.address, m.city, m.zip) == ("9582 US Highway 285", "Salida", "81201")
    assert chaffee.split_address("220 W 4th St Salida, CO 81201") == ("220 W 4th St Salida", "", "81201")
    assert chaffee.split_address("7750 Co Rd 150, Salida, CO") == ("7750 Co Rd 150", "Salida", "")
    assert chaffee.split_address("") == ("", "", "")


def test_chaffee_facebook_website_routed_to_facebook():
    m = _chaffee_detail("bighorn-apiary-llc")
    assert m.website == ""
    assert m.facebook.startswith("https://www.facebook.com/Bighorn-Apiary")
    assert m.products.split(", ")[0] == "Staples"   # taxonomy wider than the nav slugs


def test_chaffee_food_bank_hours_kept_out_of_products():
    m = _chaffee_detail("arkansas-valley-christian-mission", ["Markets/Food Banks"])
    assert m.category == "Food Bank"
    assert m.address == ""                          # no address listed
    assert m.products == ""                         # schedule fragments + type page dropped
    assert "Listed offerings: Providing food from 11:00 a.m." in m.notes
    assert m.hours == ""                            # explicit-only: not parsed into Hours


def test_chaffee_category_union_and_type_page_excluded():
    m = _chaffee_detail("valley-roots-food-hub", ["Beef/Meat", "Markets/Food Banks"])
    terms = m.products.split(", ")
    assert len(terms) == len(set(terms))
    assert "Beef/Meat" in terms and "Markets/Food Banks" not in terms


@pytest.mark.parametrize("label,exp", [
    ("Ranch", "On-Farm / Ranch Sales"), ("Farm", "On-Farm / Ranch Sales"),
    ("Market", "Farmers' Market"), ("Food Bank", "Food Bank"),
    ("Organization/Nonprofit", "Organization"), ("Co-op", "Co-op"),
])
def test_chaffee_category_map_with_unknown_passthrough(label, exp, capsys):
    html = ('<article class="provider"><h1 class="entry-title">X Farm</h1>'
            f'<p class="entry-meta"><span class="entry-terms">Provider Type: <a>{label}</a></span></p></article>')
    assert chaffee.parse_detail(html, "x").category == exp
    assert ("unknown Provider Type" in capsys.readouterr().out) == (label == "Co-op")


def test_chaffee_schedule_fragment_detection():
    for t in ["Wednesday", "and Friday", "or by appointment.", "10 a.m. - 4 p.m."]:
        assert chaffee._is_schedule_fragment(t)
    for t in ["Sunflowers", "Beef/Meat", "Staples", "Monarch honey"]:
        assert not chaffee._is_schedule_fragment(t)


def test_chaffee_fetch_skips_excluded_providers_without_fetching():
    pages = {
        f"{chaffee.BASE}/product-offerings/markets-foodbanks/": _chaffee("list_markets-foodbanks_p1"),
        f"{chaffee.BASE}/provider/arkansas-valley-christian-mission/":
            _chaffee("provider_arkansas-valley-christian-mission"),
        f"{chaffee.BASE}/provider/bighorn-apiary-llc/": _chaffee("provider_bighorn-apiary-llc"),
    }
    fetched = []

    def fake_get(url):
        fetched.append(url)
        return pages.get(url, "<html></html>")

    ms = chaffee.fetch(fake_get, exclusions={"bighorn-apiary-llc": "held for review"})
    names = {m.business_name for m in ms}
    assert "Arkansas Valley Christian Mission" in names
    assert "Bighorn Apiary, LLC" not in names
    assert f"{chaffee.BASE}/provider/bighorn-apiary-llc/" not in fetched


def test_chaffee_exclusions_file_is_valid():
    ex = chaffee.load_exclusions()
    assert ex and all(isinstance(v, str) and v for v in ex.values())


def test_chaffee_overrides_replace_scraped_values_with_provenance():
    m = _chaffee_detail("arrowpoint-cattle-company")
    chaffee.apply_overrides(m, {
        "website": {"value": "https://example.org/new"},
        "facebook": {"value": "https://www.facebook.com/x/"},
    })
    assert m.website == "https://example.org/new"        # overwrote scraped value
    assert m.facebook == "https://www.facebook.com/x/"   # filled a gap
    assert m.provenance["Website"] == m.provenance["Facebook"] == "maintainer"
    assert m.provenance["Phone"] == "chaffee_provides"   # untouched fields keep theirs


def test_chaffee_overrides_file_is_valid():
    ov = chaffee.load_overrides()
    assert ov["poncha-creek-gardens"]["website"]["value"].startswith("https://ponchacreekgardens.wordpress.com")
    assert ov["lewis-lazy-l-ranch"]["facebook"]["value"] == "https://www.facebook.com/myredcows/"


# -- provider-map page (coordinates + hide-address flags)

def test_chaffee_map_assets_parse_and_drop_shared_fallback_point():
    assets = chaffee.parse_map_assets(_chaffee("provider_map_assets"))
    assert len(assets) == 42
    arrow = assets["2010"]
    assert arrow["title"] == "Arrowpoint Cattle Company"
    assert (round(arrow["lat"], 4), round(arrow["lng"], 4)) == (38.7303, -106.0742)
    assert not arrow["hidden"]
    assert assets["2349"]["hidden"]                      # Mushroom Love Co hides its address
    # 4 providers sit on one Salida town-center point: treated as no coords
    for pid in ("2343", "2340", "2256", "2247"):
        assert assets[pid]["lat"] is None


def test_chaffee_listing_post_ids():
    ids = chaffee.parse_listing_post_ids(_chaffee("list_markets-foodbanks_p1"))
    assert ids["arkansas-valley-christian-mission"] == "2366"
    assert len(ids) == 12


def test_chaffee_map_asset_gives_coords_and_city_zip_only_when_unambiguous():
    assets = chaffee.parse_map_assets(_chaffee("provider_map_assets"))
    m = _chaffee_detail("arrowpoint-cattle-company")
    chaffee.apply_map_asset(m, assets["2010"])
    assert m.geo_source == "source" and m.latitude == assets["2010"]["lat"]
    assert (m.city, m.zip) == ("Nathrop", "81236")        # '21900 County Road 196 Nathrop Colorado 81236'
    assert m.provenance["City"] == "chaffee_provides"
    # hidden address: coords yes, nothing taken from the address text
    m2 = _chaffee_detail("arkansas-valley-christian-mission")
    chaffee.apply_map_asset(m2, assets["2366"])
    assert m2.latitude is not None and m2.city == "" and m2.address == ""
    # street mismatch -> no split guessed
    assert chaffee._map_city_zip("County Road 301 Buena Vista Colorado 81211", "CR 301") == ("", "")


def test_chaffee_fetch_end_to_end_with_map_and_map_only_provider():
    pages = {
        f"{chaffee.BASE}/product-offerings/beef-meat/": _chaffee("list_beef-meat_p1"),
        f"{chaffee.BASE}/provider/arrowpoint-cattle-company/": _chaffee("provider_arrowpoint-cattle-company"),
        chaffee.MAP_URL: _chaffee("provider_map_assets"),
    }
    ms = chaffee.fetch(lambda u: pages.get(u, "<html></html>"), exclusions={}, overrides={})
    by = {m.business_name: m for m in ms}
    assert by["Arrowpoint Cattle Company"].geo_source == "source"
    soil = by["SOIL Sangre de Cristo"]                    # on the map, on no category page
    assert soil.source_id == "post-2256" and soil.category == "Organization"
    assert soil.latitude is None                         # its point is the shared fallback
    assert soil.address == "PO Box 868 Salida Colorado 81201"
    # map-only records for providers whose slugs we listed are not duplicated
    assert sum(1 for m in ms if m.business_name.startswith("Arrowpoint")) == 1


def test_chaffee_fetch_survives_map_page_failure():
    pages = {f"{chaffee.BASE}/product-offerings/beef-meat/": _chaffee("list_beef-meat_p1"),
             f"{chaffee.BASE}/provider/arrowpoint-cattle-company/": _chaffee("provider_arrowpoint-cattle-company")}

    def get(u):
        if u == chaffee.MAP_URL:
            raise OSError("boom")
        return pages.get(u, "<html></html>")
    ms = chaffee.fetch(get, exclusions={}, overrides={})
    assert any(m.business_name == "Arrowpoint Cattle Company" and m.latitude is None for m in ms)
