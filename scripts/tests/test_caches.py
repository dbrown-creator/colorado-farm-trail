"""Offline tests for the build's run-to-run caches: the Chaffee Provides page cache
and the geocode/county cache. Goal: a rebuild repeats no network work."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrape import build, geocode
from scrape.schema import Market
from scrape.sources import chaffee_provides as chaffee


# ---- Chaffee page cache

def test_page_cache_serves_fresh_pages_without_fetching(tmp_path):
    calls = []
    fetch = lambda u: calls.append(u) or f"<html>{u}</html>"
    g = chaffee.CachedGet(cache_dir=str(tmp_path), max_age_days=7, fetcher=fetch)
    assert g("https://x.org/a/") == "<html>https://x.org/a/</html>"
    g2 = chaffee.CachedGet(cache_dir=str(tmp_path), max_age_days=7, fetcher=fetch)
    assert g2("https://x.org/a/") == "<html>https://x.org/a/</html>"
    assert calls == ["https://x.org/a/"]                   # second run: no network
    assert (g.fetched, g2.hits, g2.fetched) == (1, 1, 0)


def test_page_cache_refetches_when_stale_or_refresh(tmp_path):
    calls = []
    fetch = lambda u: calls.append(u) or "new"
    chaffee.CachedGet(cache_dir=str(tmp_path), fetcher=lambda u: "old")("https://x.org/b/")
    later = lambda: os.path.getmtime(next(tmp_path.iterdir())) + 8 * 86400
    assert chaffee.CachedGet(cache_dir=str(tmp_path), max_age_days=7, fetcher=fetch,
                             now=later)("https://x.org/b/") == "new"
    assert chaffee.CachedGet(cache_dir=str(tmp_path), refresh=True,
                             fetcher=fetch)("https://x.org/b/") == "new"
    assert len(calls) == 2


def test_fetch_defaults_to_cache(monkeypatch, tmp_path):
    made = []
    monkeypatch.setattr(chaffee, "cached_get_from_env",
                        lambda: made.append(1) or chaffee.CachedGet(
                            cache_dir=str(tmp_path), fetcher=lambda u: "<html></html>"))
    chaffee.fetch(exclusions={}, overrides={})
    assert made == [1]


# ---- geocode / county cache

def test_geocache_remembers_successes_across_runs(tmp_path):
    path = str(tmp_path / "geocode.json")
    hits = {"geo": 0, "county": 0}

    def geo(a, c, z):
        hits["geo"] += 1
        return (38.5, -106.0, "Chaffee") if a == "1 Main St" else None

    def county(lat, lon):
        hits["county"] += 1
        return "Chaffee"

    c1 = geocode.GeoCache(path=path, geocode=geo, county=county)
    assert c1.geocode_address("1 Main St", "Salida", "81201") == (38.5, -106.0, "Chaffee")
    assert c1.geocode_address("Nowhere Rd", "Salida", "") is None
    assert c1.county_for(38.123456, -106.0) == "Chaffee"
    c1.save()
    c2 = geocode.GeoCache(path=path, geocode=geo, county=county)
    assert c2.geocode_address(" 1 main st", "SALIDA", "81201") == (38.5, -106.0, "Chaffee")
    assert c2.county_for(38.1234561, -106.0) == "Chaffee"   # same point after rounding
    assert c2.geocode_address("Nowhere Rd", "Salida", "") is None   # misses are retried
    assert hits == {"geo": 3, "county": 1}
    assert geocode.GeoCache(path=path, refresh=True, geocode=geo, county=county).data["address"] == {}


def test_fill_geography_only_looks_up_blanks():
    looked = []

    class FakeCache:
        def geocode_address(self, a, c, z):
            looked.append(("geo", a))
            return (38.5, -106.0, "Chaffee")

        def county_for(self, lat, lon):
            looked.append(("county", lat))
            return "Lake"

    have_all = Market(business_name="A", latitude=38.6, longitude=-106.1, county="Fremont")
    no_county = Market(business_name="B", latitude=38.7, longitude=-106.2)
    no_coords = Market(business_name="C", address="1 Main St", city="Salida")
    build.fill_geography([have_all, no_county, no_coords], cache=FakeCache())
    assert looked == [("county", 38.7), ("geo", "1 Main St")]   # nothing for A
    assert have_all.county == "Fremont" and no_county.county == "Lake"
    assert no_coords.county == "Chaffee" and no_coords.geo_source == "census-geocoder"
