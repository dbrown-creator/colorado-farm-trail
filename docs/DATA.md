# Data Source

All farm data comes from the **Colorado Proud Farm Fresh Directory**, published by
the Colorado Department of Agriculture. It is used here purely as a **source /
attribution** — Colorado Farm Trail is an independent project (see `branding.md`).

## How the data was found

The public page — https://coloradoproud.com/find-farm-fresh-favorites/ — looked like
a WordPress store-locator, but the map is actually an **ArcGIS Experience app**
embedded in an iframe. Tracing it:

1. Page embeds an ArcGIS Experience app
   (`experience.arcgis.com/experience/c178ee51c0d747b687e58db7c9c94d32/`).
2. That app reads a Web Map item **"Farm Fresh Directory"**
   (`230a9b6cb77e4dd3931442c2ed05b746` on `COOIT.maps.arcgis.com`).
3. The web map's operational layer is a public **ArcGIS Feature Service** — the
   actual data behind the map and its table view.

## The endpoint

```
https://services3.arcgis.com/DgjqnJA1rgO92Soi/arcgis/rest/services/Farm_Fresh_Directory/FeatureServer/0
```

Query all records (attributes + lat/long) as JSON:

```
.../FeatureServer/0/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=json
```

- **163 records**, **36 counties**, **47 raw fields** each, plus point geometry
  (latitude/longitude).
- `maxRecordCount` is 2000, so a single query returns everything.

## The CSV exports (in `data/`)

| File | What |
|---|---|
| `colorado_proud_farm_fresh_directory_raw.csv` | All 47 fields, alias headers, + Latitude/Longitude. The unabridged export. |
| `farm_fresh_directory_mymaps.csv` | Cleaned, **import-ready for Google My Maps**: 22 tidy columns |

### The cleaned My Maps file

- **22 columns**: Business Name, **Category**, Address, City, County, State, Zip,
  Phone, Call first?, Website, Email, Facebook, Instagram, Hours, Months Open,
  Products, Certified Organic, SNAP, ADA Accessible, Notes, **Latitude, Longitude**.
- **`Category`** was derived from the messy raw `Operation type` field (61
  pipe-delimited combos) into **10 clean, priority-ranked buckets** for map styling:

  | Category | Count |
  |---|---|
  | Farmers' Market | 47 |
  | CSA Farm | 23 |
  | On-Farm / Ranch Sales | 22 |
  | Roadside Market | 17 |
  | U-Pick | 14 |
  | Other | 12 |
  | Agritourism | 10 |
  | Winery | 8 |
  | Garden Center / Greenhouse | 8 |
  | Restaurant | 2 |

- `Products`, `Hours`, and `Months Open` were consolidated from ~15 scattered raw
  columns into single readable cells (pipes → commas).
- **Latitude/Longitude are dedicated columns** so Google My Maps places pins exactly,
  with no geocoding.

## Deduplication & data-quality notes

The all-Colorado farmers-market dataset (`data/co_farmers_markets_all_raw.csv`)
merges two source feeds (`colorado_proud` + `usda`), which introduces
near-duplicates. These are flagged in the **`Possible Dup Of`** column and resolved
under the rules in **[`DEDUP_STANDARDS.md`](DEDUP_STANDARDS.md)** — the short version:
**location is the deciding signal** (we're making a map), and same-location
seasonal (winter/summer) markets get merged with the seasonality captured in
`Hours` / `Months Open` / `Notes`.

### The deduped file

`data/co_farmers_markets_all_deduped.csv` is the resolved output: **139 → 133
records**. The 6 duplicates below were dropped into their canonical twin, the
Backyard winter season was folded into its summer record (extended `Months Open` +
a `Notes` line), and the `Possible Dup Of` working column was cleared (decisions now
live in `DEDUP_STANDARDS.md`). The raw file is left **untouched** as the source of
record; regenerate the deduped file from it rather than editing it by hand.

**6 merges applied (dropped → canonical):**

- Backyard Market in Black Forest **- Winter** → *The Backyard Market in Black Forest*
- **Delta Farmers Market** → *The Delta Farmers Market & Bazaar*
- **Evergreen Farmers Market** (Bergen Pkwy) → *Evergreen Farmers Market THE ORIGINAL*
- **Fort Morgan Farmers' Market** → *Fort Morgan Farmers Market at The Block*
- **Aspen Grove Lifestyle Center Farmers' Market** → *Aspen Grove Farmers Market*
- **Highland United Neighbors Farmers' Market** → *Highland Farmers' Market*

### Market consolidations to reflect

- **Farmers' Market at Highlands Square** (row: 3489 W. 32nd Ave) was **folded into
  The Highlands Farmers Market** (`thehighlandsfarmersmarket.com`), a different
  entity operating at the same 32nd & Lowell location (Sundays 9am–1pm, May–Oct).
  The dead `highlandssquarefarmersmarket.com` domain is the evidence of that
  consolidation — the standalone Highlands Square market no longer exists under its
  own name. The record should be re-pointed to The Highlands Farmers Market
  identity/URL rather than kept as a separate "Highlands Square" market.
- Note this is **distinct** from **Highland Farmers' Market** (1576 Boulder St,
  `denverhighland.org`) — a different entity ~1.2 mi away in lower Highland. Same
  neighborhood name, different market and location; do not conflate the two.

## Refreshing the data

```
python scripts/fetch_farm_data.py
```

Re-pulls from the feature service and rebuilds both CSVs in `data/`. Re-import the
`farm_fresh_directory_mymaps.csv` into Google My Maps if the source directory has
changed. (The directory is community-submitted and grows over the season, so an
occasional refresh keeps the map current.)

## Importing into Google My Maps

1. mymaps.google.com → **Create a new map** → **Import** → upload
   `farm_fresh_directory_mymaps.csv`.
2. Position by **Latitude** + **Longitude** (not the address).
3. Title markers by **Business Name**.
4. Style: set *"Group places by"* → **Category** for color-coded pins.

Current live map ID (`mid`): `15fDxNgQN1yxO7xc2FR27Kq6NND3GjvE`
