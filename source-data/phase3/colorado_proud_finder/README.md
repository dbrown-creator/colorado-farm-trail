# Colorado Proud member directory (Phase 3)

The full Colorado Proud membership from
[coloradoproud.com/product-finder](https://coloradoproud.com/product-finder/): 1,557
businesses across 83 business types (crawled 2026-10-03). This is every member, not just
the Farm Fresh layer that Phase 1 and Phase 2 already use.

It's **Phase 3**, so it stays off the map. Nothing here feeds the Phase 2 build. Members
are moved onto the trail only after review.

## Files

| File | What it is |
|---|---|
| `colorado_proud_finder_raw.csv` | One row per member: every field the directory shows, plus `in_scope` and `site_categories`. |
| `colorado_proud_finder_by_category.csv` | One row per member × business type, for slicing by category. |
| `category_counts.csv` | Members per business type, and the site category each in-scope type maps to. |
| `../../../data-compiled/phase3/colorado_proud_members.csv` | The 932 in-scope members in the 22 My Maps columns, with `Already Known` (name match against Phase 1 and Phase 2) and `Status`. |

Refresh with `python scripts/phase3/colorado_proud_finder.py`. It fetches profiles only for
members it hasn't seen before. `CPF_REFRESH=1` recrawls all of them, which takes about 40
minutes.

## Scope (decided 2026-10-04)

**In:** farms and ranches, farm markets, livestock, orchards, apiaries, dairies, cheese
makers, farmers markets, roadside stands, wineries, cider mills, agritourism, meat markets
and packers, food banks, grocery/co-op/specialty food stores, bakeries, cottage-food and
value-added makers (as "Food Maker"), restaurants and caterers.

**Out:** breweries, distilleries, manufacturers, wholesalers and distributors, ag input
suppliers, food trucks, coffee shops and bars, institutions, and members outside Colorado.
The mapping lives in `TYPE_CATEGORIES` in the script.

## Known caveats

- About 16 members list the form placeholder "12345 Test St." (Arvada 80222) as their
  address. It is dropped, so their location is unknown.
- "Accessibility Test" (`business_profile_703`) is a junk listing and is skipped.
- About 60 addresses are blank or garbled at the source (repeated fields, "CO, Colorado").
- The directory doesn't show emails. Members are contacted through a message form.
- SNAP is "Yes" only when a member lists "EBT / SNAP". If it isn't listed, the field is
  left blank rather than set to "No".
- If this data is later folded into the Phase 2 build: Phase 2's 200 m proximity merge
  ignores names, so dense member data folds neighbouring businesses together. Seen on
  2026-10-04: Cortez Creamery merged into Pueblo Seed & Food. Require a shared name word
  first.
