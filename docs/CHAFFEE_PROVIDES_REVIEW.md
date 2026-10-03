# Chaffee Provides — providers held for manual review

> Status: **open**. These 6 providers are listed on chaffeeprovides.org but are
> **held out of our dataset** until they've been reviewed with the Chaffee Provides /
> Guidestone team. They are listed in
> [`source-data/phase2/chaffee_provides_exclusions.json`](../source-data/phase2/chaffee_provides_exclusions.json),
> which the scraper (`scripts/scrape/sources/chaffee_provides.py`) reads. Delete an
> entry there to let a provider back in. Full link-check evidence for all 42
> providers: [`source-data/phase2/chaffee_provides_link_review.csv`](../source-data/phase2/chaffee_provides_link_review.csv).

How this was decided (2026-10-03): every listed link was checked, and each dead
or missing one was researched online. Working rule: if we can't find any current
online presence for a business, it's probably no longer operating.

## Likely closed (3)

| Provider | What we found | Question for the team |
|---|---|---|
| **Jumpin' Good Goat Dairy** (31700 US-24, Buena Vista) | `jumpingoodgoats.com` returns 404. **Buck & Bloom Cheese Co.** says it restarted "the facility that used to be known as Jumpin' Good Goat Dairy" in spring 2025, after several dormant years ([buckandbloomcheese.com](https://www.buckandbloomcheese.com/), [Chaffee County Times](https://www.chaffeecountytimes.com/news/buck-bloom-cheese-company-colorado/article_b03fbafc-e70e-420b-bcb4-764c193f9955.html)). | Should the listing be replaced with Buck & Bloom Cheese Co.? |
| **Erin's Geothermal Greenhouse** (15990 CR 162, Nathrop) | `erinsgreenhouse.com` no longer resolves. The most recent mention is from about 2013. The owner now runs Antero Hot Springs Cabins. | Is the greenhouse still selling produce? |
| **Salida Quality Dairy** (7600 CR 146, Salida) | No website or social media. The Colorado SOS record shows the LLC **delinquent since 2024-08-01**. The only third-party listing (Beyond Organica) is on a lapsed domain. | Are they still selling herd shares? |

## Unclear (3)

| Provider | What we found | Question for the team |
|---|---|---|
| **Moonstone Farm** (355 E Rainbow Blvd, Salida) | `moonstoneventures.com` is down (DNS error). Everything online describes Moonstone Ventures as a coaching / retreat / farm-stay business. We found no farm products. | Do they produce food for sale? |
| **Snow Angel Greenhouse** (10057 Hwy 50, Poncha Springs) | The website now redirects to a *Snow Angel Coffee* Facebook page. The last greenhouse news is from March 2021. | Is the greenhouse still operating, or is it now coffee only? |
| **Bighorn Apiary, LLC** (1532 I St, Salida) | The only presence is a Facebook page with no visible recent activity, plus one old beekeeper directory entry. | Still selling honey? |

## Proposed contact-detail changes (NOT applied yet)

These providers stay in the dataset with the details Chaffee Provides currently
lists. Research turned up newer details, shown below. **None of these changes are
in the data yet**, except rows marked ✅ APPLIED. Confirm each one with the team (or the business), then apply it.
Confirmed changes go in
[`source-data/phase2/chaffee_provides_overrides.json`](../source-data/phase2/chaffee_provides_overrides.json),
which the scraper applies on every run.

### Phone numbers

| Provider | Listed now | Found online | Source |
|---|---|---|---|
| Copper Kettle Apothecary | (719) 221-3158 | (719) 530-7111 | [chamberofcommerce.com](https://www.chamberofcommerce.com/business-directory/colorado/salida/herb-shop/2027724463-copper-kettle-apothecary), several other directories |
| Salida First Presbyterian Church | (719) 239-0406 | (719) 539-6422 | [salidapresbyterian.org](https://www.salidapresbyterian.org/) (the church's own site) |
| The Grainery Ministries | (719) 207-2359 | (719) 530-9050 | [foodpantries.org](https://www.foodpantries.org/li/grainery-ministries) |
| Chaffee Cares | (719) 568-8522 | (719) 239-1318 (+ chaffeecares@gmail.com) | a local resource listing |
| Everett Ranch Beef | *(none)* | 719-530-1597 | search results / related wedding-venue listing |
| Poncha Creek Gardens | *(none)* | 720-380-2121 (+ ponchacreekgardens@gmail.com) | [their WordPress site](https://ponchacreekgardens.wordpress.com/) |

### Addresses

| Provider | Listed now | Found online | Source |
|---|---|---|---|
| Trout Creek Farm | County Road 301, Buena Vista | 28872 CR 330, Buena Vista | [troutcreekfarm.com](https://www.troutcreekfarm.com) (the farm's own site) |
| Hutchinson Ranch | 9181 US Hwy 50, Salida | 6700 Old Corral Rd, Salida | [hutchranchsalida.com](https://www.hutchranchsalida.com) (the ranch's own site) |
| Copper Kettle Apothecary | 138 W 1st St, Salida | possibly 107 F St, Salida | one directory listing only; low confidence |
| Badger Creek Ranch | 5795 County Road 2 (Cañon City) | pickup at the Ranch Annex in Coaldale; mailing PO Box 21, Coaldale 81222 | [salidachamber.org](https://salidachamber.org/business/farms-ranches-markets/badger-creek-ranch-llc/) |

### Website / social links

| Provider | Listed now | Proposed | Why |
|---|---|---|---|
| Poncha Creek Gardens | ponchacreekgardens.com | https://ponchacreekgardens.wordpress.com/our-products/ | ✅ **APPLIED** (maintainer-confirmed 2026-10-03); old domain is for sale |
| Copper Kettle Apothecary | copperkettleapothecary.com | https://copperkettleapothecary.square.site/ + [Facebook](https://www.facebook.com/copperkettleapothecary/) | old site 404s |
| Salida First Presbyterian Church | salidafirstpresbyterianchurch.org | https://www.salidapresbyterian.org/ | old domain gone |
| Badger Creek Ranch | badgercreekranch.com/grass-fed-meat | https://store.badgercreekranch.com/ | deep link 404s; store is live |
| The Grainery Ministries | thegraineryministries.org | remove the website; use [Facebook](https://www.facebook.com/graineryministries/) | domain redirects to a security-threat warning |
| Chaffee Community Resource Center | salidacaringsharing.org/the-resource-center/ | [Facebook](https://www.facebook.com/SalidaCaringSharing/) (site is "under maintenance") | deep link 404s |
| Caring & Sharing – Sanctuary Soup Kitchen | *(none)* | [Facebook](https://www.facebook.com/SalidaCaringSharing/) | same organization as above |
| Sweet Pea Farm's Wildflower Honey | *(none)* | [Facebook](https://www.facebook.com/SweetPeaFarmHoney) | on the 2026 Salida Farmers Market vendor list |
| Lewis Lazy L Ranch | *(none)* | [Facebook](https://www.facebook.com/myredcows/) | ✅ **APPLIED** (maintainer-confirmed 2026-10-03); 2025 conservation award confirms the ranch is active |
| Everett Ranch Beef | *(none)* | [Facebook](https://www.facebook.com/everettranchbeef/) | |
| Meadows Edge Farm | *(none)* | [Facebook](https://www.facebook.com/meadowsedgefarmbv/) / [Instagram](https://www.instagram.com/meadowsedgefarmbv/) | |

Note: the Instagram account @troutcreekfarm belongs to a **different** farm, so don't
attach it to Trout Creek Farm.
