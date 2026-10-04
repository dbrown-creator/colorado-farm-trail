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
| `targets.json` | The Phase 2 markets with websites that were queued for checking. |

Rebuild the CSVs and the prospect list with `python scripts/phase3/build_prospects.py`.

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
