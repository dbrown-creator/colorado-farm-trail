# Analytics & Tracking

The whole point: measure how many people use the map and which channels drive them —
because **Google My Maps itself gives owners essentially zero analytics** (no view
counts, no visitor data). So tracking lives on the landing page, not the map.

## Google Analytics 4

- **Measurement ID:** `G-PC4YFC13N6` (embedded in `index.html`, two places). It is
  domain-independent — it kept collecting through the move to the custom domain with
  no code change.
- **Data stream:** "Colorado Farm Trail" (Stream ID `15232716864`), **Stream URL set to
  `https://coloradofarmtrail.com`** (the live custom domain). Data collection confirmed
  active.
- **Property:** created under the owner's personal Google account. Add the brand Gmail
  (`coloradofarmtrail@gmail.com`) as an Admin to move analytics onto the project
  identity — see [`BRANDING.md`](BRANDING.md).

### The custom conversion event
`index.html` fires a GA4 event whenever someone clicks through to the actual map:

```js
gtag('event', 'open_map', { placement: 'hero' | 'phone_section' });
```

This is the **true conversion** — not just "landed on the page" but "actually opened
the map." In GA4, mark it as a **Key Event** (Admin → Events → toggle "Mark as key
event") so it shows as a headline metric.

Keep **Enhanced measurement** ON (default) — it auto-tracks outbound clicks, scrolls,
and session engagement.

## What to watch in GA4

| Report | Tells you |
|---|---|
| **Realtime** | Live arrivals when you post — instant confirmation tracking works |
| **Acquisition → Traffic acquisition** | Users by **source/medium** — which channel wins |
| **User attributes / Geography** | How far it's spreading across Colorado |
| **Engagement → Events → `open_map`** | How many visitors actually opened the map |
| **Engaged sessions / avg. engagement time** | Are people using it or bouncing |

## Channel tracking with UTMs

Because GA4 is on the page, UTM tags get captured. Append to the site URL per channel:

| Channel | UTM query string |
|---|---|
| Instagram | `?utm_source=instagram&utm_medium=social&utm_campaign=farm_trail_summer` |
| Facebook | `?utm_source=facebook&utm_medium=social&utm_campaign=farm_trail_summer` |
| Text/SMS | `?utm_source=sms&utm_medium=text&utm_campaign=farm_trail_summer` |
| Email | `?utm_source=email&utm_medium=email&utm_campaign=farm_trail_summer` |
| Flyer/QR | `?utm_source=flyer&utm_medium=qr&utm_campaign=farm_trail_summer` |

## Bitly (optional, complements GA4)

Wrap each UTM link in **Bitly** for a clean link + a printable **QR code** (great for
market tables / flyers). Bitly gives per-link click + scan counts; GA4 gives the deep
behavioral data. Belt and suspenders.

## Roadmap for tracking actual farm visits & sales

Views and shares are the start. The real impact metric (farm visits + dollars) comes
from the **Farm Trail Passport** check-in system — see [`gamification.md`](gamification.md).
