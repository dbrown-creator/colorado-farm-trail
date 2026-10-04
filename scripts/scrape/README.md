# Colorado farmers-market scraper — PHASE 2 (in development, NOT live)

> **This is Phase 2.** It does not touch the live Phase 1 product
> (`data-compiled/farm_fresh_directory_mymaps.csv`, built by `scripts/fetch_farm_data.py`).
> See [`../../PHASE2.md`](../../PHASE2.md) for the Phase 1 / Phase 2 boundary.
> Outputs are isolated: compiled → `data-compiled/phase2/`, raw + enrichment →
> `source-data/phase2/`. No cutover yet.

Collects **all** Colorado farmers markets into the same 22-column schema the Farm
Fresh pipeline emits (see `../../docs/DATA.md`), so the output imports into the same
Google My Maps setup. Confidence rule: **a field is only filled when a source states
it explicitly** — nothing is guessed. Every populated field records its source in a
provenance column.

## Sources (priority order — first to fill a field wins)

| Source | Access | Coverage | Notes |
|---|---|---|---|
| **Colorado Proud / Farm Fresh** (ArcGIS) | public, no key | ~48 markets | Richest per record; wins conflicts. Same endpoint as the repo's Farm Fresh pull. |
| **USDA Local Food Portal — keyed API, all 5 directories** | free key (self-service) | statewide (~105 CO markets + farms/CSAs/hubs) | `farmersmarket` + `onfarmmarket` + `csa` + `foodhub` + `agritourism`, each mapped to a `Category`. **Verified fields (farmersmarket):** name, street, city, state, zip, lat/lng, phone, email, website, Facebook/Instagram, description, `listing_id` + `updatetime` (kept as `Source ID` / `Source Updated` for the update engine). **NOT provided:** hours, season, products, SNAP, organic, county. Set `USDA_API_KEY`; narrow with `USDA_DIRECTORIES=csa,foodhub`. |
| USDA — keyless `data_share`, all 5 directories | public, no key | opt-in only: ~6 markets, 37 on-farm, 41 CSA, 12 hubs, 12 agritourism (CO, 2026-07) | Thin (name/contact/address/website, no coords). Used automatically when no key is set; real coverage for the non-market directories. |
| **CFMA member markets** (MarketWurks API) | public JSON, no key | 37 members | **Tested & confirmed.** The map is a MarketWurks embed; data is a public REST endpoint (below). Rich fields — fills exactly what USDA lacks. 26 overlap our data (enrich), 11 are new. |
| **Chaffee Provides** (chaffeeprovides.org, Guidestone Colorado) | public HTML, no key | 36 Chaffee-area providers (42 listed; 6 held for review) | **Built** (`sources/chaffee_provides.py`). Crawls the 7 category listings (paginated) → one detail page per provider, plus the `/provider-map/` page's `map-asset` attributes for **source coordinates** (32 of 36) and the per-provider *hide address* flag, which we honor. Mostly farms/ranches the statewide directories miss, plus food banks, orgs, a restaurant. Honors `Crawl-delay: 10` → ~8 min. Held-out providers: `source-data/phase2/chaffee_provides_exclusions.json`; maintainer-confirmed fixes: `chaffee_provides_overrides.json`; open questions: [`docs/CHAFFEE_PROVIDES_REVIEW.md`](../../docs/CHAFFEE_PROVIDES_REVIEW.md). Spec: [`docs/CHAFFEE_PROVIDES.md`](../../docs/CHAFFEE_PROVIDES.md). |
| **Curated new records** (`source-data/phase2/curated_records.csv`) | hand research | 7 records (first batch) | **Built** (`sources/curated.py`). For businesses no directory carries. One row per researched business with a `Status` (`add` → record; `market-only` / `skip` kept as the research log so names aren't re-researched), `Source URLs`, `Researched` date and `Found Via`. Coordinates optional (else geocoded). Provenance `curated`. First batch: the 19 food vendors on the 2026 Salida Farmers Market list that were missing from our data (7 add, 10 market-only, 3 skip). Corrections to *existing* records go in `overrides.csv` instead. |
| **Operator / organizer sites** — *not yet built* | HTML | multiple markets each | Market-management companies that run several markets, with first-party season/hours. **One site → many markets**, so high value for both discovery and enrichment. Seed list below. |
| Curated guides — *not yet built* | HTML | coverage gaps | coloradoinfo.com, ag.colorado.gov — cross-check + fill missing markets. |
| Per-site enrichment — *prototyped* | HTML + search | fills gaps | Visit each market's own website (+ search fallback) for hours/season/products/SNAP. Validated on 3 markets; see the sampling in git history. |

### CFMA member markets — confirmed data path

The `cofarmersmarkets.org` "Find a Market" map is a **MarketWurks** embed, not a
browser-only widget. Its data is a public REST API keyed by the CFMA org id:

```
GET https://app.marketwurks.com/api/vendors/activeWithFields
Header: X-Account-ID: b33b989cea991edcf0db27887992a281
```

Returns 37 member markets, each with a named `fields[]` array that maps directly to
our schema (and fills the fields USDA lacks):

| MarketWurks field | Our column | Notes |
|---|---|---|
| Market name | Business Name | |
| Market Location | Address + Latitude + Longitude | `value.textName` / `.latitude` / `.longitude` |
| Website / Facebook / Instagram | Website / Facebook / Instagram | Instagram is a `@handle` → normalize to URL |
| Market Day(s) + Market Opens/Closes | Hours | Day(s) are **0-indexed Sun=0…Sat=6** |
| Months Open + Market Starts/Ends | Months Open | Months are **0-indexed Jan=0…Dec=11** |
| Programs | SNAP | Multichoice numeric codes; decode labels once from the signup-form template (→ SNAP / Double Up / WIC) |
| Market Description | Notes | |

Build notes: org id is read from the homepage embed (`data-org-id`); validate URLs
(some source values are truncated); coords are precise (skip geocoding for these).
Companion endpoints: `/api/vendors/active` (thin), `/api/vendor-locations` (pins).

### Operator / organizer sites (seed list)

Each runs multiple Colorado markets; scrape the operator once to get authoritative
season/hours for all of them and to discover markets missing from the directories.

| Operator | URL | Markets it runs (as of 2026) | In our data? |
|---|---|---|---|
| **Jarman & Co Events** | <https://jarmanandcoevents.com/> | South Pearl Street (Denver), Breckenridge, Central Park (Denver), Riverfront (Denver), A Tavola Winter Market (Denver) | South Pearl ✓, Breckenridge ✓ — **Central Park, Riverfront, A Tavola: NEW** |

*(Add more operators here as they're found — e.g. via CFMA membership and market
websites that credit a manager.)*

Missing coordinates are filled with the free **US Census geocoder** (which also
returns county) and flagged `geo_source=census-geocoder`; county for source-provided
coords is backfilled via the free **FCC Area API**.

### Field-value priority (which source wins a conflict)

Coverage and per-field authority are **separate questions**. Directories (Colorado
Proud, CFMA, USDA) are best for *discovering* markets and for coordinates; but for the
*value* of a field, a market's own site is the authority:

1. **The market's own official website**, when it looks legitimate and states the fact
   clearly — **wins every time**, over any directory/aggregator. (e.g. Woodland Park's
   `wpfarmersmarket.com` says Friday, so Friday beats CFMA's "Thursday".)
2. **Colorado Proud** (vetted state directory) — for markets not (yet) confirmed on
   their own site.
3. **CFMA / MarketWurks** (member-maintained, rich).
4. **Chaffee Provides** (community-maintained, Chaffee County only). Maintainer-
   confirmed corrections in `chaffee_provides_overrides.json` win over its scraped
   values (provenance `maintainer`).
5. **USDA** (broad but thin/sometimes stale).
6. **Multi-aggregator consensus** > single aggregator (5280, coloradoinfo, etc.).

So the merge order is *coverage-first* (directories create records + coords), but a
**confirmed official-site value overrides** the directory value for the fields it
states, and provenance records that the override came from the official site. "Clearly
stated + legit-looking site" is the bar — ambiguous or sketchy pages don't override.

## Run — find, approve, push

Getting new data and building are separate steps, and a build repeats no work.

**1. Find: check the sources for new data (on purpose, not per build)**

```bash
python scripts/scrape/refresh_sources.py                 # all network sources
python scripts/scrape/refresh_sources.py cfma usda_api   # just these
```

Sources: `colorado_proud`, `cfma`, `chaffee_provides`, `usda_api`, `usda_datashare`.
Each writes:
- a snapshot, `source-data/phase2/snapshots/<source>.json`: the parsed records the build reads
- a change report, `snapshots/changes/<source>.csv`: what's **new / removed / changed**,
  field by field, versus the previous snapshot

A source that fails keeps its previous snapshot. Chaffee Provides reads its page cache
(`.cache/chaffee_provides/`, reused for 7 days). `CHAFFEE_REFRESH=1` forces the polite
~8-minute recrawl. After a parser change, re-run the refresh for that source.

**2. Approve:** review the change reports. Committing the snapshots (a PR) is the
approval. Hand research goes in `curated_records.csv` (new businesses) and corrections
go in `overrides.csv` (existing ones). Both are reviewed the same way.

**3. Push: build offline**

```bash
python scripts/scrape/build.py
```

The build reads only local files: snapshots, enrichment results, curated records,
dedup decisions and overrides. It merges, fills blanks and writes the outputs.
Geocode and county answers, including misses, are remembered in `.cache/geocode.json`.
Only records that are new or still blank get a lookup; misses are retried after 30
days, and `GEOCODE_REFRESH=1` redoes everything. A rebuild with nothing new takes
about a second.

The USDA key lives in **`.env` at the repo root** (git-ignored; never commit it),
as `USDA_API_KEY=...`. Only `refresh_sources.py usda_api` needs it. With a key, the
keyed pull runs and data_share is kept as a gap-filler, because the two views don't
fully overlap (observed 2026-07: CO csa had 21 keyed vs 41 opt-in data_share listings).

Outputs (Phase 2, isolated; live Phase 1 Farm Fresh CSV untouched):
- `data-compiled/phase2/co_farmers_markets_all_mymaps.csv` — 22 columns, My Maps import-ready
- `source-data/phase2/co_farmers_markets_all_raw.csv` — same + `Source` / `Geo Source` /
  `Possible Dup Of` / `Provenance`

Website / Facebook / Instagram values from every source (including enrichment and
maintainer overrides) go through `normalize.clean_url` / `facebook_url` /
`instagram_url`, the same rules the live build uses (`build_map_data.py` imports them):
bare or `@` handles become profile URLs, scheme-less URLs get `https://`, and page names
with spaces are dropped rather than written as broken links.

Enrichment inputs read from `source-data/phase2/enrichment/results/*.json` (folded at
top priority). Latest full build: **149 markets** + official-site enrichment across 109
of them (`  Possible Dup Of` flags name-stem pairs for human review; nothing is
auto-merged).

## Test

```bash
python -m pytest scripts/tests -q
```

Offline: source parsers run against saved fixtures in `scripts/tests/fixtures/`;
geocoding is not called. Covers normalize helpers, USDA mapping (real + synthetic
fixtures), and dedup/merge (overlap collapse, gap-fill provenance, coordinate-proximity
merge).

## Getting the USDA key

Self-service form: <https://www.usdalocalfoodportal.com/fe/fregisterpublicapi/>
(email + a math captcha; key is emailed back). Endpoints — one per directory:
`/api/{farmersmarket|onfarmmarket|csa|foodhub|agritourism}/?apikey=KEY&...`.
For each directory the fetcher first tries the documented single-request
`state=co` query, then falls back to the x/y/radius grid sweep. Field names are
verified against a live keyed `farmersmarket` sample; the records carry a
`directory_type` discriminator, so one parser serves all five — **spot-check the
other four directories' field names on the first keyed run**.

## Status

- ✅ Colorado Proud + USDA (keyless + keyed, schema verified) fetchers
- ✅ USDA scan widened to **all five portal directories** (on-farm markets, CSAs,
  food hubs, agritourism → `Category`); `Source ID`/`Source Updated` captured per
  record as the change-detection hook for the update engine
  (design: [`../../docs/UPDATE_ENGINE.md`](../../docs/UPDATE_ENGINE.md))
- ✅ merge/dedup, possible-dup review flag, geocode + county backfill, writer, 19 tests
- ✅ statewide build producing 139 markets
- ✅ Chaffee Provides source (category crawl + provider-map coords, exclusions/overrides
  files, offline tests). Link check + presence research for all 42 providers on
  2026-10-03 → 6 held for review with the Chaffee Provides team
- ⏳ CFMA map scrape, curated guides, per-site enrichment (to fill hours/season/
  products/SNAP for the ~91 USDA-only markets that lack them)
- ⏳ Operator-site scrape — **Jarman & Co Events** (jarmanandcoevents.com) first;
  yields new markets (Central Park, Riverfront, A Tavola) + first-party season/hours
