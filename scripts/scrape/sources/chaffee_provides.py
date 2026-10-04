"""Source: Chaffee Provides provider directory (chaffeeprovides.org, Guidestone Colorado).

The site is WordPress/Genesis with everything server-rendered as plain HTML; the
"provider map" page is a JS template we deliberately do NOT scrape. Discovery is by
crawling the category listing pages (`/product-offerings/<slug>/`, paginated), which
link to one detail page per provider (`/provider/<slug>/`). There is no REST/sitemap
shortcut (see docs/CHAFFEE_PROVIDES.md).

Markup (discovered from fixtures): every card/detail is an `<article class="... provider
type-<type> ...">`; the detail page carries `<h1 class="entry-title">` (name),
`<div class="entry-content">` (description) and `<p class="entry-meta">` holding
`<span class="entry-terms">Label: value</span>` pairs (Website, Phone, Email, Address,
Provider Type, Product Offerings). Product-offering terms are `<a rel="tag">` links.

Fetching is separate from parsing: `parse_listing` / `parse_detail` are pure so tests run
offline against saved HTML.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ..normalize import clean_url, phone
from ..schema import Market

SOURCE = "chaffee_provides"
BASE = "https://chaffeeprovides.org"
CATEGORY_SLUGS = {
    "beef-meat": "Beef/Meat",
    "dairy": "Dairy",
    "flowers": "Flowers",
    "poultry-eggs": "Poultry/Eggs",
    "spices-garlic": "Spices/Garlic",
    "veggies": "Veggies",
    "markets-foodbanks": "Markets/Food Banks",
}
# Category pages that describe the provider *type*, not a product; membership in them
# is not unioned into Products.
NON_PRODUCT_CATEGORIES = {"Markets/Food Banks"}
# Offering terms seen as real taxonomy (the nav categories plus extras like "Staples").
KNOWN_OFFERINGS = set(CATEGORY_SLUGS.values()) | {"Staples", "Food Bank"}
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CRAWL_DELAY = 10  # robots.txt `Crawl-delay: 10`; lower only deliberately (tests/fixtures)

CATEGORY_MAP = {
    "Ranch": "On-Farm / Ranch Sales",
    "Farm": "On-Farm / Ranch Sales",
    "Market": "Farmers' Market",
    "Food Bank": "Food Bank",
    "Restaurant": "Restaurant",
    "Organization/Nonprofit": "Organization",
}

SOCIAL_HOSTS = {"facebook.com": "facebook", "instagram.com": "instagram"}


# ---- fetching -----------------------------------------------------------------

def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=HDR)
    for attempt in (0, 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt:
                raise
            time.sleep(CRAWL_DELAY)
    raise RuntimeError("unreachable")


def _polite_get(url: str) -> str:
    time.sleep(CRAWL_DELAY)
    return _get(url)


# ---- page cache -----------------------------------------------------------------
# The directory changes rarely and a polite crawl takes ~8 minutes, so builds reuse
# the last downloaded pages. A page is re-downloaded only when its cached copy is older
# than CHAFFEE_MAX_AGE_DAYS (default 7), or on every page when CHAFFEE_REFRESH=1.
# Parsing always runs on the cached HTML, so parser changes apply without a recrawl.

CACHE_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".cache", "chaffee_provides"))
DEFAULT_MAX_AGE_DAYS = 7.0


def _cache_path(cache_dir: str, url: str) -> str:
    key = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("://", 1)[-1]).strip("_")
    return os.path.join(cache_dir, key + ".html")


class CachedGet:
    """A `get(url) -> html` that serves fresh cached pages and downloads the rest.
    Counts `hits` / `fetched` so the build can say whether it recrawled."""

    def __init__(self, cache_dir: str = CACHE_DIR, max_age_days: float = DEFAULT_MAX_AGE_DAYS,
                 refresh: bool = False, fetcher=_polite_get, now=time.time):
        self.cache_dir, self.max_age, self.refresh = cache_dir, max_age_days * 86400, refresh
        self.fetcher, self.now = fetcher, now
        self.hits = self.fetched = 0

    def __call__(self, url: str) -> str:
        path = _cache_path(self.cache_dir, url)
        if (not self.refresh and os.path.exists(path)
                and self.now() - os.path.getmtime(path) < self.max_age):
            self.hits += 1
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        html = self.fetcher(url)
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        self.fetched += 1
        return html


def cached_get_from_env() -> CachedGet:
    try:
        max_age = float(os.environ.get("CHAFFEE_MAX_AGE_DAYS", DEFAULT_MAX_AGE_DAYS))
    except ValueError:
        max_age = DEFAULT_MAX_AGE_DAYS
    refresh = os.environ.get("CHAFFEE_REFRESH", "").strip().lower() in ("1", "true", "yes")
    return CachedGet(max_age_days=max_age, refresh=refresh)


# ---- parsing ------------------------------------------------------------------

class _Listing(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.slugs: List[str] = []
        self.pages: List[str] = []
        self.post_ids: Dict[str, str] = {}   # slug -> WordPress post id (card's post-NNNN)
        self._post = ""

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            cls = (dict(attrs).get("class") or "").split()
            self._post = next((c[5:] for c in cls if re.fullmatch(r"post-\d+", c)), "")
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        m = re.search(r"/provider/([^/?#]+)/?", href)
        if m and self._post:
            self.post_ids.setdefault(m.group(1), self._post)
        if m and m.group(1) not in self.slugs:
            self.slugs.append(m.group(1))
        if re.search(r"/page/\d+/?$", href):
            self.pages.append(href)


def parse_listing(html: str) -> Tuple[List[str], List[str]]:
    """Return (provider slugs in page order, pagination hrefs found on the page)."""
    p = _Listing()
    p.feed(html)
    return p.slugs, p.pages


def parse_listing_post_ids(html: str) -> Dict[str, str]:
    """{provider slug: WordPress post id} for the cards on a listing page."""
    p = _Listing()
    p.feed(html)
    return p.post_ids


class _Detail(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.name = ""
        self.type_class = ""
        self.desc: List[str] = []
        self.terms: List[dict] = []   # [{"text": str, "links": [(text, href)]}]
        self.modified = ""
        self._in_h1 = False
        self._in_content = 0          # div depth inside entry-content
        self._block = False           # an open <li>/<p> that needs a separator
        self._term: Optional[dict] = None
        self._a: Optional[list] = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "meta" and a.get("property") == "article:modified_time":
            self.modified = a.get("content") or ""
        if tag == "article" and "provider" in cls and not self.type_class:
            self.type_class = next((c for c in cls if c.startswith("type-") and c != "type-provider"), "")
        if tag == "h1" and "entry-title" in cls:
            self._in_h1 = True
        if tag == "div" and (self._in_content or "entry-content" in cls):
            self._in_content += 1
        if self._in_content and tag in ("p", "li", "br", "h2", "h3", "h4"):
            self.desc.append("\n")
        if tag == "span" and "entry-terms" in cls:
            self._term = {"text": "", "links": []}
        if tag == "a" and self._term is not None:
            self._a = [a.get("href") or "", ""]

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_h1 = False
        if tag == "div" and self._in_content:
            self._in_content -= 1
        if tag == "a" and self._a is not None and self._term is not None:
            self._term["links"].append((self._a[1].strip(), self._a[0]))
            self._a = None
        if tag == "span" and self._term is not None:
            self.terms.append(self._term)
            self._term = None

    def handle_data(self, data):
        if self._in_h1:
            self.name += data
        if self._term is not None:
            self._term["text"] += data
            if self._a is not None:
                self._a[1] += data
        elif self._in_content:
            self.desc.append(data)


def _clean_text(parts: List[str]) -> str:
    text = "".join(parts).replace("\xa0", " ").replace("�", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


_DAYS = re.compile(r"\b(mon|tues?|wed(nes)?|thu(rs?)?|fri|sat(ur)?|sun)(day)?s?\b", re.I)


def _is_schedule_fragment(term: str) -> bool:
    """Food-bank listings type their hours into the Product Offerings box, so WordPress
    splits the prose on commas into 'terms' ('Wednesday', 'and Friday', '... 11:00 a.m.').
    Those are not products; they're kept in Notes instead."""
    return bool(re.search(r"\d", term) or _DAYS.search(term) or re.match(r"(and|or)\s", term, re.I))


def _split_term(term: dict) -> Tuple[str, str]:
    label, _, value = term["text"].partition(":")
    return label.strip(), value.strip()


_STATE_ZIP = re.compile(r"[,\s]+CO(?:lorado)?\.?(?:[,\s]+(\d{5})(?:-\d{4})?)?(?:[,\s]+USA)?\s*$", re.I)


def split_address(text: str) -> Tuple[str, str, str]:
    """'9582 US Highway 285, Salida CO 81201' -> (street, city, zip). City/zip are only
    returned when the text states them next to a 'CO' marker; bare rural addresses like
    '21900 County Road 196' stay whole (a 5-digit house number is not a zip)."""
    text = re.sub(r"\s+", " ", text or "").strip()
    m = _STATE_ZIP.search(text)
    if not m:
        return text, "", ""
    parts = [p.strip() for p in text[:m.start()].split(",") if p.strip()]
    if len(parts) >= 2:
        return ", ".join(parts[:-1]), parts[-1], m.group(1) or ""
    return (parts[0] if parts else ""), "", m.group(1) or ""


def _route_url(m: Market, url: str) -> None:
    """Facebook/Instagram pages listed as a 'website' go to their own columns."""
    url = clean_url(url)
    if not url:
        return
    host = urlparse(url).netloc.lower()
    for dom, attr in SOCIAL_HOSTS.items():
        if host == dom or host.endswith("." + dom):
            m.set(attr, url, SOURCE)
            return
    m.set("website", url, SOURCE)


def parse_detail(html: str, slug: str, categories: Optional[List[str]] = None) -> Optional[Market]:
    """Parse one `/provider/<slug>/` page into a Market. `categories` = human labels of the
    category listing pages the provider appeared on (unioned into Products)."""
    p = _Detail()
    p.feed(html)
    name = re.sub(r"\s+", " ", p.name).strip()
    if not name:
        return None

    m = Market(source=SOURCE, source_id=slug)
    m.set("business_name", name, SOURCE)

    fields: Dict[str, str] = {}
    offerings: List[str] = []
    for t in p.terms:
        label, value = _split_term(t)
        if label == "Product Offerings":
            offerings = [txt for txt, _ in t["links"] if txt] or [
                v.strip() for v in value.split(",") if v.strip()]
        else:
            fields[label] = value

    ptype = fields.get("Provider Type", "")
    if ptype:
        if ptype in CATEGORY_MAP:
            m.category = CATEGORY_MAP[ptype]
        else:
            print(f"  chaffee_provides: unknown Provider Type {ptype!r} ({slug}); kept verbatim")
            m.category = ptype

    street, city, zc = split_address(fields.get("Address", ""))
    m.set("address", street, SOURCE)
    m.set("city", city, SOURCE)
    m.set("zip", zc, SOURCE)

    m.set("phone", phone(fields.get("Phone", "")), SOURCE)
    m.set("email", fields.get("Email", ""), SOURCE)
    _route_url(m, fields.get("Website", ""))

    stray = [t for t in offerings if _is_schedule_fragment(t)]
    if stray:  # the box held prose: keep only real taxonomy terms as products
        stray = [t for t in offerings if t not in KNOWN_OFFERINGS]
    offerings = [t for t in offerings if t not in stray]
    seen, products = set(), []
    for term in list(offerings) + [c for c in categories or [] if c not in NON_PRODUCT_CATEGORIES]:
        if term.lower() not in seen:
            seen.add(term.lower())
            products.append(term)
    m.set("products", ", ".join(products), SOURCE)

    note = _clean_text(p.desc).replace("\n", " ")
    if stray:
        note = " | ".join(x for x in [note, "Listed offerings: " + ", ".join(stray)] if x)
    m.set("notes", note, SOURCE)
    m.source_updated = p.modified
    return m


# ---- orchestration ------------------------------------------------------------

def crawl_categories(get=_polite_get, post_ids: Optional[Dict[str, str]] = None) -> Dict[str, List[str]]:
    """Walk every category listing (following pagination) -> {provider slug: [labels]}.
    If `post_ids` is given it is filled with {slug: WordPress post id}."""
    members: Dict[str, List[str]] = {}
    for slug, label in CATEGORY_SLUGS.items():
        url, n = f"{BASE}/product-offerings/{slug}/", 1
        while url:
            html = get(url)
            slugs, pages = parse_listing(html)
            if post_ids is not None:
                post_ids.update(parse_listing_post_ids(html))
            for s in slugs:
                if label not in members.setdefault(s, []):
                    members[s].append(label)
            nxt = f"{BASE}/product-offerings/{slug}/page/{n + 1}/"
            url = nxt if any(pg.rstrip("/") == nxt.rstrip("/") for pg in pages) else None
            n += 1
    return members


# Providers held out pending manual review with the Chaffee Provides team
# (docs/CHAFFEE_PROVIDES_REVIEW.md). Keyed by slug; delete an entry to re-admit it.
EXCLUSIONS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
    "source-data", "phase2", "chaffee_provides_exclusions.json"))


def load_exclusions(path: str = EXCLUSIONS) -> Dict[str, str]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("excluded", {})
    except (OSError, ValueError):
        return {}


OVERRIDES = os.path.join(os.path.dirname(EXCLUSIONS), "chaffee_provides_overrides.json")
OVERRIDE_SOURCE = "maintainer"


def load_overrides(path: str = OVERRIDES) -> Dict[str, dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("overrides", {})
    except (OSError, ValueError):
        return {}


def apply_overrides(m: Market, fields: dict) -> None:
    """Maintainer-confirmed corrections win over the scraped value (unlike Market.set,
    which only fills gaps)."""
    for attr, spec in fields.items():
        value = spec.get("value") if isinstance(spec, dict) else spec
        if attr in ("website", "facebook", "instagram"):
            value = clean_url(value)
        elif attr == "phone":
            value = phone(value)
        setattr(m, attr, "")
        m.set(attr, value, OVERRIDE_SOURCE)


# ---- provider-map page -------------------------------------------------------
# /provider-map/ embeds every provider as <div class="map-asset" asset-*="...">, including
# the coordinates Chaffee Provides cached from its own Google geocoding and a
# per-provider "hide address" flag. We read the attributes only; the page's JS also
# writes geocodes back to the site via admin-ajax, which we never call.

MAP_URL = f"{BASE}/provider-map/"
# A point shared by this many providers is the site's town-center fallback, not a
# real location: leave those records for our own geocoder instead.
SHARED_POINT_MIN = 3


class _MapAssets(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.assets: List[dict] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div" and "map-asset" in (a.get("class") or "").split():
            self.assets.append({k[6:]: (v or "").strip() for k, v in a.items()
                                if k.startswith("asset-")})


def _point(a: dict) -> tuple:
    return (round(a["lat"], 5), round(a["lng"], 5))


def parse_map_assets(html: str) -> Dict[str, dict]:
    """{post id: asset} from the provider-map page. Each asset gets parsed `lat`/`lng`
    (None when missing, malformed, or a shared fallback point) and a bool `hidden`."""
    p = _MapAssets()
    p.feed(html)
    out: Dict[str, dict] = {}
    for a in p.assets:
        try:
            lat, lng = (float(x) for x in a.get("latlng", "").split(","))
        except ValueError:
            lat = lng = None
        a["lat"], a["lng"] = lat, lng
        a["hidden"] = a.get("hide-address", "").lower() in ("true", "1")
        if a.get("post-id"):
            out[a["post-id"]] = a
    counts: Dict[tuple, int] = {}
    for a in out.values():
        if a["lat"] is not None:
            counts[_point(a)] = counts.get(_point(a), 0) + 1
    for a in out.values():
        if a["lat"] is not None and counts[_point(a)] >= SHARED_POINT_MIN:
            a["lat"] = a["lng"] = None
    return out


def _map_city_zip(asset_address: str, street: str) -> Tuple[str, str]:
    """The map address is '<street> <City> Colorado <zip>'. Only trust city/zip when it
    starts with the street we already have, so the split point is unambiguous."""
    addr = re.sub(r"\s+", " ", asset_address or "").strip()
    if not street or not addr.lower().startswith(street.lower()):
        return "", ""
    m = re.fullmatch(r"[,\s]*([A-Za-zñÑ .'-]+?),?\s+(?:CO|Colorado)\s+(\d{5})", addr[len(street):])
    return (m.group(1).strip(), m.group(2)) if m else ("", "")


def apply_map_asset(m: Market, asset: dict) -> None:
    if asset.get("lat") is not None:
        m.latitude, m.longitude, m.geo_source = asset["lat"], asset["lng"], "source"
    if asset.get("hidden"):
        return  # provider asked Chaffee Provides not to show its address
    city, zc = _map_city_zip(asset.get("address", ""), m.address)
    m.set("city", city, SOURCE)
    m.set("zip", zc, SOURCE)


def market_from_asset(asset: dict) -> Optional[Market]:
    """A provider that is on the map but on no category page."""
    name = re.sub(r"\s+", " ", asset.get("title", "")).strip()
    if not name:
        return None
    m = Market(source=SOURCE, source_id=f"post-{asset.get('post-id', '')}")
    m.set("business_name", name, SOURCE)
    ptype = asset.get("type", "")
    if ptype == "Institution/Nonprofit":  # the map's own JS renames this label too
        ptype = "Organization/Nonprofit"
    m.category = CATEGORY_MAP.get(ptype, ptype or m.category)
    if not asset.get("hidden"):
        m.set("address", re.sub(r"\s+", " ", asset.get("address", "")), SOURCE)
    m.set("phone", phone(asset.get("phone", "")), SOURCE)
    m.set("email", asset.get("email", ""), SOURCE)
    _route_url(m, asset.get("website", ""))
    m.set("notes", re.sub(r"\s+", " ", asset.get("description", "")), SOURCE)
    if asset.get("lat") is not None:
        m.latitude, m.longitude, m.geo_source = asset["lat"], asset["lng"], "source"
    return m


def fetch(get=None, exclusions: Optional[Dict[str, str]] = None,
          overrides: Optional[Dict[str, dict]] = None) -> List[Market]:
    """`get` defaults to the page cache (see CachedGet); pass any `get(url) -> html`
    to bypass it (tests pass fixtures)."""
    if get is None:
        get = cached_get_from_env()
    excluded = load_exclusions() if exclusions is None else exclusions
    overrides = load_overrides() if overrides is None else overrides
    post_ids: Dict[str, str] = {}
    members = crawl_categories(get, post_ids)
    try:
        assets = parse_map_assets(get(MAP_URL))
    except Exception as e:  # coords are a bonus; never lose the listings over them
        print(f"  chaffee_provides: provider-map fetch failed ({e}); no source coords")
        assets = {}
    out: List[Market] = []
    for slug, cats in members.items():
        if slug in excluded:
            print(f"  chaffee_provides: skipping {slug} (held for review: {excluded[slug]})")
            continue  # never fetched
        m = parse_detail(get(f"{BASE}/provider/{slug}/"), slug, cats)
        if not m:
            continue
        if post_ids.get(slug) in assets:
            apply_map_asset(m, assets[post_ids[slug]])
        if slug in overrides:
            apply_overrides(m, overrides[slug])
        out.append(m)
    # Providers on the map but on no category page (e.g. SOIL Sangre de Cristo).
    # Keyed "post-<id>" in the exclusions/overrides files.
    known = set(post_ids.values())
    for pid, asset in assets.items():
        key = f"post-{pid}"
        if pid in known or key in excluded:
            continue
        m = market_from_asset(asset)
        if m:
            if key in overrides:
                apply_overrides(m, overrides[key])
            out.append(m)
    if isinstance(get, CachedGet):
        print(f"  chaffee_provides: {get.hits} pages from cache, {get.fetched} downloaded "
              f"(refresh with CHAFFEE_REFRESH=1)")
    return out
