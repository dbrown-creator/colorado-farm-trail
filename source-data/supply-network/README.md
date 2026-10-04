# Colorado restaurant supply network (pilot)

Who supplies Colorado restaurants, shops and markets. Every link was traced from a
published, citable source. It's seeded from Rootstalk Breckenridge's supplier list
(rootstalkbreck.com/culinary-beverage) and expanded one hop each way:

- suppliers' own buyer, stockist and distributor pages
- other Colorado restaurants that name their farms
- press roundups

Researched 2026-10-03.

## Files

**`edges.csv`**: one row per supplier → buyer link, in the direction product flows.

| Column | Meaning |
|---|---|
| `supplier`, `buyer` | Business names; they match `nodes.csv` `name` |
| `date` | Year (or year-month) of the evidence; `unknown` when the page is undated |
| `confidence` | `high`: the supplier or buyer names the other on its own page or menu. `medium`: press, or a third party. `low`: old or indirect |
| `source` | URL of the evidence |
| `note` | e.g. `family-owned`, `same owner`, `owner-operated` |

**`nodes.csv`**: one row per business.

| Column | Meaning |
|---|---|
| `type` | `farm`, `maker`, `distributor`, `restaurant`, `retail` or `market` |
| `out`, `inn` | Number of buyers / number of suppliers in this pilot |
| `on_trail`, `trail_match` | Matching listing on the farm-trail map (`data/markets.json`). `exact` is a name match; `possible` should be checked by hand |

## Scraped sources

`scripts/supply_network/stockists.py <source>` reads a producer's published stockist
table (WordPress TablePress tables, which many small producers use) into
`scraped/<source>.csv`. Merging into `edges.csv` is a separate step, because each
stockist is classified by hand as food-service, food retail or non-food retail
(gift shops, garden centers). Non-food stockists are kept but carry that note.

| Source | Stockists | Last run |
|---|---|---|
| `bee_squared` (bethsbees.com) | 75 rows, 68 businesses (chains merged) | 2026-10-03 |

## Known gaps

- Every restaurant sourcing page and town-listing article in the pilot is fully loaded,
  with names checked against the live source on 2026-10-03. That covers Potager, Duo,
  Element 47, Clean Kitchen, Urban Farmer, The Regional, Floradora and others. Entries the
  source no longer shows were dropped. A handful of suppliers from press-only mentions with
  no town (e.g. Taste Local, Mountain Tap, Aurum Steamboat) are still unloaded.
- Scope is Colorado plus neighboring states (e.g. Bootheel 7 Ranch, Lusk WY). Producers from
  farther away are left out (Maine seafood and a Minnesota hog co-op on Potager's and Duo's
  lists). Colorado-based brands that source elsewhere (Teton Waters, Tender Belly) stay in, noted.
- Element 47's purveyor page lists a lamb processor that closed in 2020, so its other links
  may be stale even though the page is live.
- Distributors (Growers Organic, UNFI, Farm Runners, Loco, What Chefs Want) publish no
  account lists, so the links through them are thin.
- Many restaurant links come from 2014–2019 press; re-check those before using them on the map.

The wholesale growers' "Where to Get It" lists on the map draw on these links.
