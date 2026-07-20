# Gamification — The Farm Trail Passport

> Status: **designed, not built.** Deliberately parked so Phase 0 (map + site +
> analytics) can launch first. This doc captures the vision so we can pick it up
> without re-deriving it.

## The idea

Turn the static map into a **road-trip check-in game**. Drivers pull up Colorado
Farm Trail, visit farms/markets/U-picks, and **check in** at each stop. Every
check-in stamps their **Passport**, climbs the **leaderboards**, and adds to a live
**"dollars driven to Colorado farms this summer"** counter.

The scoreboard isn't just engagement — it *is* the farmer-impact proof (visits +
dollars) that makes growers, press, and sponsors care.

## The one-line pitch

> Colorado Farm Trail is a free road-trip game — drive the state, check in at farms
> along the way, stamp your Passport, climb the leaderboards, and watch the community
> rack up real dollars for local growers. Eat local, and prove it.

---

## Check-in mechanics

A check-in should take ~15 seconds from a phone:

- **Which farm** (dropdown of the 163 — pre-filled if launched from a map pin)
- **What you bought** (short text / quick categories)
- **Roughly what you spent** ($ — self-reported)
- **Photo** (optional)
- **Feature my story?** (optional opt-in → source for testimonials)
- Handle / display name (leaderboards show **handles, not real names**)

## Leaderboards

- 🥇 **Most farms visited**
- 🗺️ **Most counties** (the "collect the state" mechanic — great for road-trippers)
- ✅ **Most check-ins**
- 💵 **Most dollars to farmers** (the impact leaderboard)
- 🌻 **Community total** — live tally of visits + $ across everyone (the headline number)

## Badges

Keep people coming back:
- **First Stop** — your first check-in
- **Trailblazer** — 5 farms
- **County Collector** — farms in N different counties
- **Century Club** — $100+ reported to farmers
- **Regional trails** — complete the Western Slope / Front Range / etc. trail

---

## Build path (no-code first)

**Phase 1 — The Passport (a weekend, free, no code):**
1. **Google Form** = the check-in (farm dropdown, what bought, $ spent, photo, story opt-in).
2. Responses → **Google Sheet** automatically.
3. **Looker Studio** (free) connects to the Sheet → renders live leaderboards +
   the community $ counter.
4. Embed the Looker dashboard on the landing page; link the Form from every map pin.

Result: a working game, zero code.

**Phase 2 — Level up (when traction justifies it):**
- Turn the Sheet into a real app with **Glide** or **Softr** (still no-code):
  personal passports, auto-badges, logins.
- **Farmer pulse-check:** a monthly one-tap "seeing Trail visitors?" to a handful of
  farms → qualitative corroboration of the self-reported impact.
- **Stories:** the opt-in field feeds real users to feature; a small thank-you / gift
  card for a great story is a cheap, powerful content engine.

---

## Measuring farmer impact

- **Hard numbers:** total check-ins, unique farms, self-reported $ → the "dollars
  driven" story.
- **Honest caveat:** self-reported spend is *directional, not accounting* — people
  forget or round. Frame it as *"$X+ reported by the community,"* which is credible.
- **Corroboration:** farmer pulse-check + user stories triangulate the self-report
  into a believable impact narrative.

## Guardrails

- **Privacy:** handles not real names on leaderboards; no sensitive data collected;
  everything opt-in.
- **Anti-gaming:** leaderboards can be gamed — keep stakes light/fun; consider
  photo-required check-ins or per-day caps if abuse shows up. Don't over-engineer
  before there's a real audience.
