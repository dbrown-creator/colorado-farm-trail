# Roadmap

The guiding principle: **launch now, layer on the rest.** Don't let the (exciting)
gamification vision stall a simple, live, tracked map this summer.

## Phase 0 — Live & tracked *(in progress — tonight's goal)*

A public map + a landing page that measures views and shares.

- [x] Pull & clean the 163-farm dataset (`DATA.md`)
- [x] Build the Google My Map, color-coded by category
- [x] Set the map to public (Anyone with link → Viewer)
- [x] Build the landing page (`index.html`)
- [x] Wire in GA4 (`G-PC4YFC13N6`) + the `open_map` conversion event
- [ ] **Publish on GitHub Pages** (repo `dbrown-creator/colorado-farm-trail`)
- [ ] Point GA4 Data Stream URL at the live site
- [ ] Confirm tracking in GA4 **Realtime**
- [ ] Smoke test on a phone (map loads, button works, looks right)

### Remaining publish steps tonight
1. Push `index.html` to the repo root (already there locally).
2. **Settings → Pages** → Source: Deploy from branch → `main` / root → Save.
3. Live at `https://dbrown-creator.github.io/colorado-farm-trail/`.
4. GA4 → **Admin → Data Streams** → set that URL.
5. Open the live URL on your phone → confirm GA4 **Realtime** shows an active user.

## Phase 1 — The Farm Trail Passport *(designed, not built)*

Turn the map into a check-in road-trip game with leaderboards and a live
"dollars driven to farmers" counter. No-code: Google Form → Sheet → Looker Studio.
Full spec in [`gamification.md`](gamification.md).

## Phase 2 — Level up *(later)*

- No-code app (Glide/Softr): personal passports, auto-badges, logins.
- Farmer pulse-checks + user stories → real impact narrative.
- Brand-out: dedicated Gmail, socials, logo, maybe a domain.

---

## Backlog / parked decisions

- [ ] **Domain** — `cofarmtrail.org` was explored but **not registered**. Custom-domain
      DNS setup for GitHub Pages is documented below for when a domain is actually
      acquired.
- [ ] **Dedicated brand Gmail** — move map/site/GA4/socials off the personal account
      (preferred: `coloradofarmtrail@gmail.com`).
- [ ] Logo / wordmark.
- [ ] Instagram + Facebook accounts.
- [ ] Refresh the dataset mid-season (`python scripts/fetch_farm_data.py`).

---

## Reference: custom domain on GitHub Pages (for later)

When a domain is registered, point it at GitHub Pages (`dbrown-creator.github.io`):

**CNAME record (primary `www` subdomain):**
| Type | Host | Value |
|---|---|---|
| CNAME | `www` | `dbrown-creator.github.io` |

**A records (apex → redirects to www):**
| Type | Host | Value |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |

Then: delete any registrar parking records that conflict → GitHub Pages → **Check
again** → once green, tick **Enforce HTTPS**. Note: setting a custom domain commits a
`CNAME` file to the repo — don't delete it when re-uploading `index.html`.
