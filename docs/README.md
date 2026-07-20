# Colorado Farm Trail

A free road-trip map + guide to Colorado's local food scene — 163 farms, farmers'
markets, U-picks, roadside stands, and wineries across 36 counties, all on one map
that drops right into the Google Maps app on your phone.

> **Tagline:** *"Find your next farm stop."*
> **Mission:** get as many Coloradans as possible eating local — and driving real
> dollars to local growers — this summer.

---

## Status (as of July 2026)

| Piece | Status |
|---|---|
| Data pulled & cleaned (163 farms) | ✅ Done — see [`DATA.md`](DATA.md) |
| Google My Map built & set public | ✅ Done |
| Landing page (`index.html`) | ✅ Built, GA4 wired in |
| Google Analytics 4 | ✅ Measurement ID `G-PC4YFC13N6` embedded |
| Hosting (GitHub Pages) | ⏳ In progress — repo `dbrown-creator/colorado-farm-trail` |
| Custom domain (`cofarmtrail.org`) | ⛔ Not registered yet — parked for later |
| Dedicated brand Gmail | ⛔ Later — using personal account for now |
| Gamification (Farm Trail Passport) | 🔮 Designed, not built — see [`gamification.md`](gamification.md) |

**Live map (public):**
https://www.google.com/maps/d/viewer?mid=15fDxNgQN1yxO7xc2FR27Kq6NND3GjvE

---

## What's in this repo

| File / folder | What it is |
|---|---|
| `index.html` | The landing page — embeds the map, runs GA4, has a tracked "Open the map" button |
| [`branding.md`](branding.md) | Brand identity, the naming exercise, decisions, and open naming/domain TODOs |
| [`gamification.md`](gamification.md) | The Farm Trail Passport concept — check-ins, leaderboards, badges, phased build |
| [`ANALYTICS.md`](ANALYTICS.md) | GA4 setup, the `open_map` event, Bitly + UTM tracking plan, metrics to watch |
| [`DATA.md`](DATA.md) | Where the data came from (ArcGIS), the endpoint, fields, and how to refresh it |
| [`MARKETING.md`](MARKETING.md) | Ready-to-post share copy for every channel + the launch checklist |
| [`ROADMAP.md`](ROADMAP.md) | Phases 0 → 1 → 2, what's next tonight, and the backlog |
| [`ROLLOUT.md`](ROLLOUT.md) | This year's go-to-market — the multi-season frame + a week-by-week launch plan |
| [`MONETIZATION.md`](MONETIZATION.md) | How to earn from the map without breaking trust — sponsorship, Passport, grants, licensing |
| `data/` | The cleaned + raw CSV exports of the farm directory |
| `scripts/fetch_farm_data.py` | Re-pulls the source data from ArcGIS and rebuilds both CSVs |

---

## Quick start (view the site locally)

The page is a single self-contained HTML file. Just open it:

```
# double-click index.html, or serve it:
python -m http.server 8000
# then visit http://localhost:8000
```

## Deploying

Hosted on **GitHub Pages** from this repo (`main` branch, root folder). Push
`index.html` to the root and enable Pages under **Settings → Pages**. See
[`ROADMAP.md`](ROADMAP.md) for the full publish + custom-domain checklist.

## Refreshing the farm data

```
python scripts/fetch_farm_data.py
```

Re-pulls all records from the Colorado Proud ArcGIS feature service and rebuilds
`data/farm_fresh_directory_mymaps.csv` (import-ready for Google My Maps) and the
raw export. See [`DATA.md`](DATA.md).
