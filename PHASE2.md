# Phase 2 is LIVE (cutover 2026-10-04)

The map at coloradofarmtrail.com is built from the **Phase 2** combined dataset:
`data-compiled/phase2/co_farmers_markets_all_mymaps.csv` -> `scripts/build_map_data.py` ->
`data/markets.json` -> `index.html`. The type chips are the filter groups in
`scripts/scrape/categories.py`.

To update the map: change Phase 2 inputs (snapshots, `curated_records.csv`,
`overrides.csv`, `dedup_decisions.csv`), run `python scripts/scrape/build.py`, then
`python scripts/build_map_data.py`, and commit all three outputs.

**Rollback:** revert the cutover PR. It only changed `build_map_data.py`'s source path,
the page (`index.html`, `about.html`) and `data/markets.json`; every Phase 1 file is
still in place.

## The former Phase 1 files: now a Phase 2 input

The Colorado Proud Farm Fresh pipeline still runs, but its output feeds Phase 2
(`scripts/scrape/sources/farm_fresh.py`) instead of the map directly.

| Role | Path |
|---|---|
| Farm Fresh compiled file (Phase 2 input) | `data-compiled/farm_fresh_directory_mymaps.csv` |
| Raw source | `source-data/colorado_proud_farm_fresh_directory_raw.csv` |
| Fetch script (with CATEGORY_ / FIELD_CORRECTIONS) | `scripts/fetch_farm_data.py` |

## Phase 2 — the data behind the live map

An expanded, all-Colorado farmers-market dataset that merges multiple sources
(Colorado Proud + CFMA/MarketWurks + USDA) and enriches each market from its own
official website. Everything Phase 2 is namespaced under `phase2/`:

| Role | Path |
|---|---|
| Build + reconcile code | `scripts/scrape/` (see its README) |
| Compiled map-ready output | `data-compiled/phase2/co_farmers_markets_all_mymaps.csv` |
| Deduped compiled variant | `data-compiled/phase2/co_farmers_markets_all_deduped.csv` |
| Full raw + provenance export | `source-data/phase2/co_farmers_markets_all_raw.csv` |
| Per-site enrichment inputs | `source-data/phase2/enrichment/` (targets + `results/*.json`) |
| Curated cross-check (Bright Garden) | `source-data/phase2/brightgarden_*.csv` |
| Phase 2 site pages (market calendar) | `_phase2/*.html`. GitHub Pages' Jekyll build skips `_` folders, so these can't go live early. `scripts/build_phase2_preview.py` copies them into the preview. |
| Market schedule parser (Hours → calendar sessions) | `scripts/market_schedule.py` |

Folder convention (matches the rest of the repo): **`source-data/` = raw / collected
source data**, **`data-compiled/` = finished compiled products**.

## Cutover (later)

When Phase 2 is ready, a deployment plan will decide how the expanded dataset replaces
or augments the live Phase 1 map. Until then, Phase 1 stays as the single source of
truth for the live site. Target: revisit ~next week.
