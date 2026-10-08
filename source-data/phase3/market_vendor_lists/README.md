# Market vendor lists (Phase 3 prospect source)

Vendor names captured from the vendor lists that Colorado farmers markets publish, used to
build the Phase 3 prospective-farm list (`data-compiled/phase3/prospective_farms.csv`).

**Nothing here is researched.** Each vendor is recorded exactly as its market's list shows it:
name, the list's section heading, and the town and product blurb only when the list states
them. Prospects need their own verification before they go anywhere near the map.

## Files

| File | What it is |
|---|---|
| `raw/<market-slug>.json` | One per market checked: whether it publishes a list, the list URL and season, site status, notes, and every vendor captured. |
| `markets_checked.csv` | One row per market (generated). |
| `all_vendors.csv` | One row per vendor × market, with a farm signal (generated). |
| `county_by_city.csv` | City → county lookup (hand-maintained input). Reused from the Phase 2 dataset's Census/FCC-derived counties; `Basis` marks hand-keyed rows and `Note` flags cities that span counties. |
| `county_overrides.csv` | Researched per-vendor county corrections (input). Wins over everything else. |
| `targets.json` | The Phase 2 markets with websites that were queued for checking. |

Rebuild the CSVs and the prospect list with `python scripts/phase3/build_prospects.py`.

## County columns

`all_vendors.csv` and `prospective_farms.csv` carry `County` and `County Source`. The source says
how the county was found, in order of trust: `manual` (a researched row in `county_overrides.csv`),
`location_stated` (the town the market's list gives for that vendor), `market_city` (the market's
own town, a fallback only: vendors often come from a neighboring county, e.g. Delta County
growers at Crested Butte), or `unresolved` (no usable town, e.g. the "Denver metro" markets).
A prospect sold at several markets with no stated town lists each market town's county.

The counties are saved in the CSVs and rebuilt identically each run from the raw JSON plus the two
input files above, so reruns never lose them. To fix one, add a row to `county_overrides.csv`
(blank `Market` = applies at every market) and rerun the build.

## Coverage (checked 2026-10-03)

- 142 Phase 2 markets that have a website were checked: 41 publish a vendor list, 69 don't,
  32 couldn't be checked. The unchecked ones had dead domains, bot blocks, JS-only pages, or
  sites that were hijacked or now redirect to unrelated content.
- The 22 Phase 2 markets without a website weren't checked.
- Facebook/Instagram-only lists aren't captured.

## Capture rules

- A list counts when it names vendors on the market's own site, a document that site links,
  or the operator's site for that market. Application pages, vendor counts ("70+ vendors"),
  and two or three named examples don't count.
- Operator-wide lists are recorded once, not copied to each market. For example, Metro Denver
  Farmers' Market's "MDFM Legends" list is in `metro-denver-farmers-market-operator-wide.json`.
- Shared multi-market lists are filtered to the market being recorded. The BCFM list is split
  into Boulder and Longmont by its market codes.
- Stale lists are kept with their season (Boulder/Longmont 2025, Eagle 2024, Fort Collins
  Winter 2025-26, Green Valley Ranch 2024).
- MarketWurks lists (Montrose, Nederland) are read from the public API with each market's
  `org-id`, and their category codes are decoded from the signup form, the same way as
  `scripts/scrape/sources/cfma.py`.

## Known caveats

- Golden's list is published only as images and was typed by eye, so names may have small
  spelling slips.
- Black Forest and The Backyard Market in Black Forest are the same single-week lineup
  (October 3).
- The Pueblo lists come from a homepage carousel and are probably partial.
- Vail lists vendors under both its Sunday and Thursday markets.
- Some Harvey Park and Ridgway section headings were assigned from the page layout.
