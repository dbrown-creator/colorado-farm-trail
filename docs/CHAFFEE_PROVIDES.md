# Chaffee Provides scrape — requirements for implementation

> **Status: implemented 2026-10-03** (`scripts/scrape/sources/chaffee_provides.py`, wired
> into `build.py` after CFMA). The original requirements are kept below. Where the
> implementation departed from them, see "Implementation notes" at the end.
> Open review items for the Chaffee Provides team: [`CHAFFEE_PROVIDES_REVIEW.md`](CHAFFEE_PROVIDES_REVIEW.md).
>
> *Original status: requirements / handoff doc.* Target: a new Phase 2 source module.
> Written 2026-07-21 from a live recon of chaffeeprovides.org (all site facts below
> verified that day). Phase 2 rules apply throughout — see [`../PHASE2.md`](../PHASE2.md):
> outputs stay under `phase2/`, and the live Phase 1 files are **never touched**.

## Goal

Ingest the provider directory behind ChaffeeProvides.org (Guidestone Colorado's
local-food site for Chaffee County) as a new source in the Phase 2 pipeline
(`scripts/scrape/`), mapped into the same 22-column `Market` schema every other
source uses. Expected yield: **~40–60 unique providers** — mostly farms and
ranches, which complements the market-heavy statewide data (these look like the
records USDA's `onfarmmarket` directory misses).

**Strategic context** (see [`GUIDESTONE.md`](GUIDESTONE.md)): Emma at Guidestone
wants a new home for exactly this data — the site's own map is outdated. This
scrape is the *bootstrap*: it gets Chaffee coverage now and gives us a concrete
"here's your data, live on the statewide map" artifact for the August meeting.
If Guidestone later hands over their source data first-party, that export becomes
the higher-priority source and this scraper becomes the change-detector. Design
for that: keep `parse()` separate from fetching, and record `source_id` per
provider so records can be reconciled against a future Guidestone export.

## Site facts (verified 2026-07-21)

- WordPress (Genesis / Mai Theme child, WP Engine hosting). The provider map page
  itself is a custom theme template (`page-asset-map.php`) — **do not scrape the
  map**; all data is server-rendered plain HTML on the pages below. No JS
  rendering needed anywhere.
- **Category listing pages** at `/product-offerings/<slug>/` for seven slugs:
  `beef-meat`, `dairy`, `flowers`, `poultry-eggs`, `spices-garlic`, `veggies`,
  `markets-foodbanks`. Listing pages **paginate** (`.../page/2/` observed on
  markets-foodbanks at 12 cards/page) — follow pagination.
- Each card links to a **provider detail page** at `/provider/<slug>/` carrying:
  business name, provider type label, phone, email, street address, website,
  product-offerings terms, and a full description. Cards on listing pages carry a
  subset of the same fields.
- **Provider type labels** observed: `Ranch`, `Farm`, `Market`, `Restaurant`,
  `Organization/Nonprofit`, `Food Bank`.
- **Product-offerings taxonomy is wider than the seven nav slugs** — e.g. Bighorn
  Apiary shows offering "Staples". Capture the terms verbatim; don't assume the
  seven-slug list is exhaustive.
- **No API shortcuts**: the `provider` CPT is not exposed over REST
  (`/wp-json/wp/v2/provider` → 404; it's absent from `/wp-json/wp/v2/types`), and
  there is no sitemap (`/wp-sitemap.xml`, `/sitemap_index.xml` → 404; no
  `Sitemap:` line in robots.txt). Crawling the category pages is the discovery
  mechanism.
- **No coordinates** appear in the rendered HTML. Geocoding fills the gap
  (existing pipeline behavior).
- **robots.txt**: only `/wp-admin/` disallowed, but `Crawl-delay: 10` — respect
  it (see Politeness).
- Addresses are often street-only, rural-county-road style (`21900 County Road
  196`, `7980 CR 250`), frequently with no city or zip. Some listings (food
  banks, orgs) have no address at all.

## Deliverable 1 — source module `scripts/scrape/sources/chaffee_provides.py`

Follow the existing source-module shape (`colorado_proud.py`, `cfma.py`):
module-level `SOURCE = "chaffee_provides"`, thin `fetch_*` functions doing I/O,
**pure `parse()` functions that take fetched content and return
`List[Market]`** so tests run offline against fixtures, and a top-level
`fetch() -> List[Market]`.

### Crawl plan

1. For each of the seven category slugs: GET the listing page, follow
   `/page/N/` pagination until exhausted.
2. From cards, collect the set of `/provider/<slug>/` URLs, remembering which
   category page(s) each provider appeared on.
3. GET each provider detail page once (a provider on four category pages is
   fetched once — dedupe by slug before fetching).
4. Parse detail pages into `Market` records; category-page membership feeds
   `Products` (below).

### Field mapping

All writes go through `Market.set(attr, value, SOURCE)` — the confidence rule
holds: **only fill what the page states explicitly; nothing inferred**.

| Page field | Column | Notes |
|---|---|---|
| Business name | Business Name | |
| Provider type label | Category | via CATEGORY_MAP below |
| Street address | Address | as shown; do NOT invent city/zip |
| City / Zip | City / Zip | only if the address text actually contains them (e.g. "220 W 4th St Salida, CO 81201" → split; use/extend `cfma._split_address`-style parsing + `normalize.zipcode`) |
| County | *(leave empty)* | do NOT hardcode "Chaffee" — some providers sit over the line (Badger Creek Ranch's CR 2 address may be Fremont Co.); the FCC coord-backfill in `build.fill_geography` handles it honestly |
| Phone | Phone | `normalize.phone` |
| Email | Email | |
| Website | Website | `normalize.clean_url`; some providers list a Facebook page as their website — if the URL is facebook.com/instagram.com, route it to Facebook/Instagram instead of Website |
| Product-offerings terms + category-page membership | Products | union of both, deduped, comma-joined, human labels (e.g. "Beef/Meat, Poultry/Eggs, Staples") |
| Description | Notes | full description text; hours often live inside prose ("food pantry Tuesdays & Thursdays 11–2") — leave them in Notes, do NOT parse into Hours (explicit-only rule) |
| Provider slug | source_id | stable key for reconciling against a future Guidestone export |
| `<meta property="article:modified_time">` (if present) | source_updated | check the detail page head; WP/SEO plugins usually emit it. Omit if absent |

Latitude/Longitude: never set — leave for `fill_geography` (`geo_source`
becomes `census-geocoder`). Expect a visible failure rate on the "CR 196"-style
addresses with no city; those records simply ship without coords and surface in
the raw CSV for manual review. That is correct behavior, not a bug.

### Category mapping

```python
CATEGORY_MAP = {
    "Ranch": "On-Farm / Ranch Sales",
    "Farm": "On-Farm / Ranch Sales",
    "Market": "Farmers' Market",
    "Food Bank": "Food Bank",              # new Category value
    "Restaurant": "Restaurant",            # new Category value
    "Organization/Nonprofit": "Organization",  # new Category value
}
```

Unknown labels: keep verbatim and print a warning (don't drop the record).
See Open decision #1 on whether the three new category values ship at all.

### Politeness / fetching

- Honor the site's `Crawl-delay: 10`: sleep 10s between requests. Full crawl is
  roughly 10 pagination pages + ~50 detail pages ≈ 10 minutes — fine for a build
  step, but make the delay a module constant so tests/fixture-refresh can lower
  it consciously.
- Reuse the repo convention: `urllib.request` with the existing Mozilla UA
  header, 60s timeout. **No new dependencies for fetching.**
- One retry on transient 5xx, then raise — `build.collect()` should wrap the
  call in try/except like it does CFMA, so a Chaffee outage never kills the
  statewide build.

### HTML parsing — no new hard dependency (Open decision #2)

The repo is stdlib-only so far. Default: parse with `html.parser`
(`HTMLParser` subclass) targeting the card/detail markup. Snapshot the real
markup into fixtures FIRST, then write selectors against what's actually there
(class names were not captured during recon — discover them from the fixtures,
and note them in the module docstring). If the markup proves too messy for
stdlib parsing, adding `beautifulsoup4` is acceptable — but that's a repo-wide
dependency decision; flag it in the PR rather than burying it.

## Deliverable 2 — wire into `build.py`

Add to `collect()` **after CFMA, before USDA** (community-maintained directory:
below the vetted state directory and member-maintained CFMA, above thin/stale
USDA — consistent with the field-value priority ladder in the scrape README).
Same failure isolation as CFMA (try/except with a printed warning).

## Deliverable 3 — fixtures + offline tests

Match `scripts/tests/test_scrape.py` style; everything runs offline, no
network, geocoding untouched.

- Fixtures in `scripts/tests/fixtures/`: one real category listing page
  (ideally `markets-foodbanks` page 1 — it exercises all six type labels), its
  page 2 (pagination), and 2–3 real detail pages including one address-less
  food bank and one street-only ranch.
- Tests to include, minimum:
  - listing parse finds all 12 provider URLs + the page-2 link
  - detail parse maps every field per the table above (assert provenance
    labels, e.g. `m.provenance["Phone"] == "chaffee_provides"`)
  - category-membership union → Products (provider on two category pages gets
    both terms, deduped)
  - facebook-as-website routing; phone/zip normalization on real messy values
  - CATEGORY_MAP including the unknown-label passthrough
  - no City/County invented when the address lacks them

## Deliverable 4 — docs

- Add a row to the source table in `scripts/scrape/README.md` (+ status
  bullet), mirroring the CFMA entry's level of detail.
- One line in `GUIDESTONE.md` noting the scrape exists and is the bootstrap for
  the Guidestone data conversation.

## Acceptance criteria

- `python scripts/scrape/build.py` completes with the new source active;
  statewide output grows by roughly 40–60 rows; Chaffee-area records appear
  with `Source` containing `chaffee_provides`.
- `python -m pytest scripts/tests -q` passes offline.
- No files outside `scripts/`, `docs/`, `data-compiled/phase2/`,
  `source-data/phase2/` are modified. Phase 1 artifacts untouched.
- Re-running the build is idempotent (same input pages → same rows).
- Spot-check in raw CSV: Arrowpoint Cattle Company, Bighorn Apiary, and one
  food bank look right (fields, provenance, category, products).

## Non-goals

- Do not scrape or reverse-engineer the map template/JS — the listing pages are
  the data source.
- Do not parse hours/season/SNAP out of description prose (explicit-only rule;
  the per-site enrichment pass is the mechanism for that later).
- No outreach automation — the Guidestone relationship is handled by David.
- No auto-merge behavior changes; existing merge/dup-flag logic applies as-is.

## Open decisions (defaults chosen; override in the PR if David says otherwise)

1. **Do Food Bank / Restaurant / Organization records ship into the statewide
   dataset?** Default: **yes, ingest them** with the new Category values —
   Guidestone's food-access framing is part of the partnership pitch, and
   filtering downstream is trivial. Alternative: parse them but hold them out of
   the compiled CSV.
2. **Parser dependency**: stdlib `html.parser` (default) vs adding
   `beautifulsoup4`.
3. **Merge-priority position**: after CFMA / before USDA (default, per above).
   For Chaffee-area records that also exist in Colorado Proud/USDA, this means
   Chaffee Provides fills gaps but doesn't override the state directory.

## Implementation notes (2026-10-03)

Corrections to the recon facts above, and decisions made while building:

- **The provider-map page *does* carry coordinates.** `/provider-map/` embeds every
  provider as `<div class="map-asset" asset-*="...">` with `asset-latlng` (the site's own
  cached Google geocodes), the full address, and `asset-hide-address`. We read those
  attributes. We don't run or reverse-engineer the map JS, and we never call its
  `admin-ajax` `store_latlng` write-back. Results:
  - **Coordinates:** 32 of 36 records get source coordinates (`geo_source=source`).
  - **Town-center fallback:** a point shared by 3 or more providers is the site's
    Salida fallback, not a real location (4 providers sit on it today). Those records
    fall through to our geocoder.
  - **Hide address:** when a provider has it set, we take coordinates (the site pins
    them publicly too) but no address, city or zip. This matches the address-privacy
    concern in `GUIDESTONE.md`.
  - **City / zip:** filled from the map address only when that address starts with the
    detail page's street, so the split point is unambiguous.
- **42 providers on the map vs 41 on the category pages.** The extra one, SOIL Sangre de
  Cristo, is built from its map entry (`source_id = post-<id>`).
- **Product Offerings is free text for food banks.** WordPress splits their typed hours
  into fake terms ("Wednesday", "and Friday"). If any term looks like a schedule
  fragment, every term outside the known taxonomy moves to Notes ("Listed offerings:
  ..."), not Products. The *Markets/Food Banks* category page describes a provider
  type, so it's never added as a product.
- **Address parsing is stricter than `cfma._split_address`.** Rural addresses like
  "21900 County Road 196" would turn the house number into a zip, so city and zip come
  only from text next to a `CO` marker.
- **Exclusions and overrides files** (`source-data/phase2/`):
  - `chaffee_provides_exclusions.json`: providers held out pending review. They're
    never fetched.
  - `chaffee_provides_overrides.json`: maintainer-confirmed corrections. They overwrite
    scraped values, with provenance `maintainer`.
  - Both are keyed by provider slug, or `post-<id>` for map-only providers.
- **Link check and presence research (2026-10-03):** see
  `source-data/phase2/chaffee_provides_link_review.csv`. 6 providers held: 3 likely
  closed, 3 unclear.
- **Open decision #1 (ship food banks / orgs / restaurant): shipped**, with the new
  Category values `Food Bank`, `Organization` and `Restaurant`. **#2: stdlib
  `html.parser`** was enough, no new dependency. **#3: after CFMA, before USDA**, as
  proposed.

