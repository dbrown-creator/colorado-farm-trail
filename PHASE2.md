# Phase 1 (LIVE) vs Phase 2 (in development)

This repo currently ships **Phase 1** and develops **Phase 2** side by side. They are
deliberately isolated so Phase 2 work can never disturb the live product. **No cutover
has happened yet** — Phase 2 is not deployed.

## Phase 1 — LIVE. Do not modify as part of Phase 2 work.

The shipping product: a Google My Maps directory built from the **Colorado Proud Farm
Fresh** directory only.

| Role | Path |
|---|---|
| Live compiled map file | `data-compiled/farm_fresh_directory_mymaps.csv` |
| Raw source | `source-data/colorado_proud_farm_fresh_directory_raw.csv` |
| Build script | `scripts/fetch_farm_data.py` |
| Site | `index.html` |

Anything under Phase 2 must leave these **in place and unmodified**.

## Phase 2 — in development. NOT live.

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

Folder convention (matches the rest of the repo): **`source-data/` = raw / collected
source data**, **`data-compiled/` = finished compiled products**.

## Cutover (later)

When Phase 2 is ready, a deployment plan will decide how the expanded dataset replaces
or augments the live Phase 1 map. Until then, Phase 1 stays as the single source of
truth for the live site. Target: revisit ~next week.
