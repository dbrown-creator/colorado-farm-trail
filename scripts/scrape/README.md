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
| **USDA Local Food Portal — keyed API** | free key (self-service) | statewide (~105 CO) | Statewide breadth. **Verified fields:** name, street, city, state, zip, lat/lng, phone, email, website, Facebook/Instagram, description. **NOT provided:** hours, season, products, SNAP, organic, county. Set `USDA_API_KEY` env var. |
| USDA — keyless `data_share` | public, no key | only ~6 (opt-in) | Thin (name/contact/address/website). Cross-check only; used automatically when no key is set. |
| **CFMA member markets** (MarketWurks API) | public JSON, no key | 37 members | **Tested & confirmed.** The map is a MarketWurks embed; data is a public REST endpoint (below). Rich fields — fills exactly what USDA lacks. 26 overlap our data (enrich), 11 are new. |
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
4. **USDA** (broad but thin/sometimes stale).
5. **Multi-aggregator consensus** > single aggregator (5280, coloradoinfo, etc.).

So the merge order is *coverage-first* (directories create records + coords), but a
**confirmed official-site value overrides** the directory value for the fields it
states, and provenance records that the override came from the official site. "Clearly
stated + legit-looking site" is the bar — ambiguous or sketchy pages don't override.

## Run

```bash
python scripts/scrape/build.py                    # no key: Colorado Proud + thin data_share
USDA_API_KEY=xxxx python scripts/scrape/build.py  # adds the rich statewide USDA pull
```

Outputs (Phase 2, isolated; live Phase 1 Farm Fresh CSV untouched):
- `data-compiled/phase2/co_farmers_markets_all_mymaps.csv` — 22 columns, My Maps import-ready
- `source-data/phase2/co_farmers_markets_all_raw.csv` — same + `Source` / `Geo Source` /
  `Possible Dup Of` / `Provenance`

Enrichment inputs read from `source-data/phase2/enrichment/results/*.json` (folded at
top priority). Latest full build: **149 markets** + official-site enrichment across 109
of them (`Possible Dup Of` flags name-stem pairs for human review; nothing is
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
(email + a math captcha; key is emailed back). Endpoint:
`/api/farmersmarket/?apikey=KEY&x=LON&y=LAT&radius=MILES`. `build.py` sweeps a grid of
points across Colorado and dedupes. **Verify `sources/usda.py::parse_api` field names
against a real response** the first time the key is used — it was written from the
documented schema, not a live keyed sample.

## Status

- ✅ Colorado Proud + USDA (keyless + keyed, schema verified) fetchers
- ✅ merge/dedup, possible-dup review flag, geocode + county backfill, writer, 19 tests
- ✅ statewide build producing 139 markets
- ⏳ CFMA map scrape, curated guides, per-site enrichment (to fill hours/season/
  products/SNAP for the ~91 USDA-only markets that lack them)
- ⏳ Operator-site scrape — **Jarman & Co Events** (jarmanandcoevents.com) first;
  yields new markets (Central Park, Riverfront, A Tavola) + first-party season/hours
