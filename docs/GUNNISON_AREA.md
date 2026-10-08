# Gunnison area research (2026-10-08)

Research log for the Gunnison Valley pass. Hand-researched records are in
`source-data/phase2/curated_records.csv` (`Status` add / market-only / call / skip, with
`Source URLs`); corrections are in `source-data/phase2/overrides.csv`.

## Where the dataset stands

Gunnison County places in the dataset: **6 before, 11 now**.

| Category | Before | Added | Now |
|---|---|---|---|
| Farmers' Market | 2 | 0 | 2 (Crested Butte, Gunnison) |
| Farm / ranch / CSA / hub | 1 (Cranor Charolais) | 3 | 4 (+ Mountain Roots Food Project, Parker Pastures, LB Specialty Beef) |
| Restaurant | 0 | 1 | 1 (The Sunflower) |
| Grocery / food maker | 2 | 1 | 3 (+ Gunnison Vitamin & Health Food Store) |
| Winery | 1 | 0 | 1 |

Parker Pastures and LB Specialty Beef publish no street address, so they are town-only: they
have a county but no map pin (the geocoder can't place them).

## Verified vs needs a call

**Verified, added (Gunnison County):** Mountain Roots Food Project (own site, 2026 CSA;
farm field addresses not published), The Sunflower (own site + 5280 2026; hours not published),
Gunnison Vitamin & Health Food Store (own site + CSU Extension).
**Added, town only, call recommended:** Parker Pastures (a conflicting LocalHarvest listing at
57564 US Hwy 50 was not used), LB Specialty Beef (own site dated 2025; CSU Extension 2026).

**Need a call (logged, not on the map):** Gunnison Gardens (address/phone are secondhand; no
site or social), Two Twelve (site dated 2025), Mountain Earth Organic Grocer, Crested Butte
Catering Co., Revelden, Peterson Ranch / Double J, Rockin J Spear Cattle Co, Rivergate Ranch
(Powderhorn), Tassinong Farms (likely skip).
Also unconfirmed in the existing data: Honey Moon Mesa (MarketSpread says Paonia, our data says
Hotchkiss; no site found), Miss Penn's Mountain Seeds (Westcliffe; operating unconfirmed),
The Yurtstead (site dated 2025).

**Lake City / Hinsdale County:** no confirmed recurring farmers market (a 2024 "Wednesday
Market" listing is unconfirmed; chamber 970-944-2527). No verified producers found in
Almont, Ohio City, Pitkin, Parlin, Sapinero, Marble or Somerset. The Mountain Roots producer
marketplace (localfoodmarketplace.com) would not load and is worth a manual look.

## Crested Butte Farmers Market vendors from other counties

Of the 14 farm-signal vendors, none verified as Gunnison County except possibly Gunnison Gardens
(a call is needed). Saved as `County Source = manual` in
`source-data/phase3/market_vendor_lists/county_overrides.csv`.

| Vendor | County | Town |
|---|---|---|
| Birdstory Nursery | Delta | Paonia (added) |
| Honey Moon Mesa | Delta | Hotchkiss/Paonia (already in dataset) |
| Mountain Bird (Gray Acres Farm) | Delta | Paonia (added) |
| Mushroom Mesa | Delta | Crawford (market-only, not mapped) |
| Osito Farms | Delta | Hotchkiss (added) |
| Pantoja's Family Farms | Delta | Delta (market-only, not mapped) |
| Rock 'n Roots Farm | Delta | Paonia (already in dataset) |
| Thistle Whistle Farm | Delta | Hotchkiss (added) |
| Zephyros Farm and Garden | Delta | Paonia (already in dataset; address, phone, website filled) |
| Pedro's Farms LLC | Montrose | Pea Green, mailing city Delta (probable; no source states the county) |
| The Yurtstead LLC | Montrose | near Montrose (market-only, not mapped) |
| The Stone Fruit Company | Mesa | Palisade (already in dataset) |
| Miss Penn's Mountain Seeds | Custer | Westcliffe (already in dataset) |
| Gunnison Gardens | Gunnison (unverified) | Gunnison (call) |

## Source quality caveats

- The Crested Butte vendor page returned no text when fetched; membership comes from each
  vendor's MarketSpread listing and the existing Phase 3 capture.
- Several fields (Gunnison Gardens, Yurtstead address, Osito address) came from directory
  snippets, not pages opened directly; they are noted in each record.
- Counties for new records were inferred from the town; no source states county, except where
  noted. Pedro's Farm should get a parcel check.
- Pedro's Farm phone now follows its own site (970-200-6919) over the directory number.

## Supply-network leads (not yet added to `source-data/supply-network`)

Parker Pastures and LB Specialty Beef -> Gunnison Vitamin & Health Food Store (CSU Extension
local-beef page); Mountain Roots Food Project -> Two Twelve (Two Twelve's own site; Two Twelve
needs a call).

## Farm Runners producer list (added 2026-10-08)

Source: <https://www.farmrunners.com/farmers>, a Western Slope delivery company's 57 producers.
12 were already in the dataset (Abundant Life, Ela Family Farms, Honey Rock Landing, The Living Farm,
M & H Ag, Mattics, Osito, Pantoja, Princess Beef, Roaring Fork Mill, Valley Roots Food Hub, Vermont
Sticky) and 2 came from the Crested Butte research (Mountain Bird, Thistle Whistle). Of the other 45
(plus 4 that turned out to be in the dataset under another spelling: Big B's, Tuxedo Corn, Homestead
Natural Meats, Rocking W Cheese, and DeVries):

- **Added (8):** Berry Fungi Farms, Fortunate Fruit, High Desert Seed + Gardens, Western Culture
  Farmstead & Creamery, Rancho Durazno, Zia Tortilla Co. (a tortilla maker, not a farm), plus
  Topp Fruits and Grand Valley Micro Farms (town-only, pinned at the town center).
- **Market-only, not mapped (5):** Delectamenti Eats, Farmhand's Harvest, Fassett Hay & Cattle,
  Rogers Mesa Fruit Co., White Mountain Farm.
- **Need a call (22):** see [`CALL_LIST.md`](CALL_LIST.md).
- **Skipped, nothing verifiable (5):** Grey Owl Gardens, Producer's Co-Op (a feed/fuel co-op),
  Stuarts Farm, Zimmerman Farms, GroFresh.

The Farm Runners page loads its producer list with JavaScript; the owners/products/towns used
here came from reading it in a browser. Mountain Bird and Thistle Whistle's Farm Runners names are
"Mountain Bird Poultry" and "Thistle Whistle".
