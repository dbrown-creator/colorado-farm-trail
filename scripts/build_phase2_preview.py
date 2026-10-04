#!/usr/bin/env python3
"""Build a local preview of the live map running on Phase 2 data (cutover step 2 draft).

Writes preview/phase2/ (git-ignored): a copy of index.html + about.html whose type
chips are the map filter groups from scripts/scrape/categories.py, and a
data/markets.json built from the Phase 2 output by the live builder
(build_map_data.py), so links and fields are normalized exactly as on the site.

The copy drops Google Analytics (preview visits must not count as site traffic)
and shows a "Phase 2 preview" banner. Nothing under the live site changes.

Usage:  python scripts/build_phase2_preview.py
        npx serve preview/phase2 -l 3015
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import build_map_data  # noqa: E402
import market_schedule  # noqa: E402
from scrape import categories  # noqa: E402

OUT_DIR = REPO / "preview" / "phase2"
PHASE2_CSV = REPO / "data-compiled" / "phase2" / "co_farmers_markets_all_mymaps.csv"

# Chip colors per group (index.html's pins/chips need a color, emoji and short label).
STYLE = {
    "markets": ("#3f7d3a", "Markets"), "farms": ("#8a6d3b", "Farms"),
    "agritourism": ("#2f8f8f", "Agritourism"), "csa": ("#c77d24", "CSA"),
    "stands": ("#d94f4f", "Stands"), "upick": ("#c2417a", "U-Pick"),
    "garden": ("#4a9d5b", "Garden"), "wineries": ("#7a4fb0", "Wineries"),
    "shops": ("#2f6f9f", "Shops"), "dining": ("#5a6b8c", "Dining"),
    "wholesale": ("#6f7f2a", "Wholesale"), "assistance": ("#a94f28", "Food Help"),
}
LABEL = {key: label for key, label, _, _ in categories.GROUPS}


def build_data() -> int:
    (OUT_DIR / "data").mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "data" / "markets.json"
    build_map_data.SRC, build_map_data.OUT = PHASE2_CSV, out
    build_map_data.main()
    markets = json.loads(out.read_text(encoding="utf-8"))
    for m in markets:
        # The market calendar (calendar.html) reads parsed sessions; markets only.
        if "Farmers' Market" in (m.get("categories") or [m["category"]]):
            m["schedule"] = market_schedule.parse_schedule(
                m.get("hours") or "", ", ".join(m.get("monthsOpen") or []))
        labels = m.get("categories") or [m["category"]]
        groups = categories.groups_for(", ".join(labels))
        m["labels"] = labels                                   # precise data labels
        m["badges"] = [categories.BADGES[b] for b in labels if b in categories.BADGES]
        m["categories"] = [LABEL[g] for g in groups] or ["Other"]
        m["category"] = m["categories"][0]
    out.write_text(json.dumps(markets, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    return len(markets)


def build_page(n: int) -> None:
    html = (REPO / "index.html").read_text(encoding="utf-8")
    cats = ",\n".join(
        f'    "{LABEL[key]}": {{ color:"{STYLE[key][0]}", emoji:"{emoji}", short:"{STYLE[key][1]}" }}'
        for key, _, emoji, _ in categories.GROUPS)
    cats += ',\n    "Other": { color:"#7c7c7c", emoji:"📍", short:"Other" }'
    html, k = re.subn(r"  var CATS = \{.*?\n  \};", "  var CATS = {\n" + cats + "\n  };", html,
                      count=1, flags=re.S)
    assert k == 1, "CATS block not found in index.html"
    # Wholesale-only listings: the chip label changed.
    html = html.replace('catKeysOf(m).join() === "Wholesale Grower"',
                        f'catKeysOf(m).join() === "{LABEL["wholesale"]}"')
    # No analytics from a local preview: drop the GA loader, make gtag() a no-op and
    # skip its config call. The rest of that script block (share + tracking helpers
    # the page calls) must stay.
    html = re.sub(r'<script async src="https://www\.googletagmanager\.com/gtag/js[^>]*></script>', "",
                  html)
    html = html.replace("function gtag(){dataLayer.push(arguments);}", "function gtag(){}")
    html = re.sub(r"gtag\('config',[^)]*\);", "", html)
    # "Other" stays as the style fallback but gets no chip (no listing should land there).
    html = html.replace("var TYPE_ORDER = Object.keys(CATS);",
                        'var TYPE_ORDER = Object.keys(CATS).filter(function(k){ return k !== "Other"; });')
    html = re.sub(r"\b16[35]\b(?= (Colorado|farms|stops|shown))", str(n), html)
    banner = ('<div style="position:fixed;top:0;left:50%;transform:translateX(-50%);z-index:9999;'
              'background:#3a2f12;color:#ffd77a;font:600 13px system-ui;padding:4px 12px;'
              'border-radius:0 0 8px 8px">Phase 2 preview — local only, not the live site</div>')
    html = html.replace("<body", "<!--phase2-preview--><body", 1)
    html = re.sub(r"(<body[^>]*>)", r"\1" + banner, html, count=1)
    html = html.replace('<a class="map-credit" href="about.html">',
                        '<a class="map-credit" href="calendar.html">📅 Market calendar</a>\n'
                        '    <a class="map-credit" href="about.html">', 1)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    for extra in ("about.html", "og-image.png"):
        if (REPO / extra).exists():
            shutil.copy2(REPO / extra, OUT_DIR / extra)
    # Phase 2 pages wait in _phase2/ (GitHub Pages' Jekyll build skips "_" folders,
    # so they can't go live before the cutover). The preview gets them with the banner.
    # Town + ZIP coordinates for the calendar's "near a place" search (build_places.py).
    places = REPO / "source-data" / "phase2" / "places" / "co_places.json"
    if places.exists():
        shutil.copy2(places, OUT_DIR / "data" / "places.json")
    for page in sorted((REPO / "_phase2").glob("*.html")):
        text = re.sub(r"(<body[^>]*>)", r"\1" + banner, page.read_text(encoding="utf-8"), count=1)
        (OUT_DIR / page.name).write_text(text, encoding="utf-8")


def main() -> None:
    n = build_data()
    build_page(n)
    print(f"Phase 2 preview: {n} listings -> {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
