# Gunnison Valley Provides — prototype

A **working-title** local-food map and directory for the Gunnison Valley, built from the
Colorado producers data set, to show Mountain Roots Food Project what such a resource could
look like. **Local only. Not published. Not an official site.** Every page carries the banner
"Prototype for review, prepared by Colorado Farm Trail. Not the official site.", a
`noindex, nofollow` meta tag, and `robots.txt` disallows everything. No Mountain Roots
branding is used.

Built on the Chaffee Provides draft (`feat/chaffee-provides-site`): same design system, `app.js`
and map code, same build approach.

## Run it

```bash
npx serve gunnison-valley -l 3018
```

Or the `gunnison-valley` entry in `.claude/launch.json` (port 3018). `serve.json` turns off
clean-URL redirects, which would drop `?id=` / `?q=` query strings.

## Rebuild the data

```bash
python scripts/gunnison_site/build_site_data.py
# options: --inputs <repo checkout>  --counties Gunnison,Hinsdale  --producers <colorado-producers-data checkout>
```

Reads Phase 2 (`source-data/phase2/co_farmers_markets_all_raw.csv`) for the chosen counties
(default Gunnison), adds anything in the public producers data set that Phase 2 lacks, and
reads verification dates from `source-data/phase2/enrichment/results/`. Phase 3 market-vendor
names are **counted, not shown**: they are unresearched leads. If `all_vendors.csv` gains a
`County` column, the count uses it; until then it uses the market's city. As research lands
(merged Phase 2 data, curated records), rebuild and new places appear.

## Pages

`index.html` home · `find-food.html` map with search, product filters, map key, town filter ·
`provider.html?id=` detail page · `list-your-business.html` listing / update flow (the form
opens an email in this prototype) · `about.html` how it works, monthly verification, sources.

## Before this could be real

- The listing form needs a reviewed intake that feeds the data set.
- Monthly verification is described, not yet automated for this area.
- Thin data: only the places found so far; most of the valley's producers are missing.
- Basemap is OpenStreetMap's public tiles; use a keyed provider under its own domain.
- Name, contact address and ownership are placeholders.
