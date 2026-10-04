#!/usr/bin/env python3
"""Turn a market's free-text Hours + Months Open into calendar sessions.

The directory data says things like "Sat: 8:30am - 2:00pm (Jun 6 - Sep 4); Sat:
9:00am - 2:00pm (Sep 5 - Oct 3)" with a separate "June, July, ..." months list. The
calendar page needs to know, for any date, which markets are open and when, so this
parses each Hours string into sessions:

    {"days": [6], "open": "08:30", "close": "14:00", "closeText": null,
     "from": "2026-06-06", "to": "2026-09-04", "dates": null, "months": null}

- days: weekdays, Mon=1 ... Sun=7 (ISO). Empty for one-off dated sessions.
- open/close: 24h "HH:MM". close is None when the text says "dusk" (closeText).
- Season, most specific wins: dates (one-off dates) > from/to (a stated date range)
  > months (a month range stated with that session) > the market's Months Open.
  When none of those exist the page shows the session with a "season not listed" note.

Anything the parser can't read cleanly marks the schedule `approx` (the page then
says "varies, check before you go" and shows the original text). A segment with no
readable time, such as "By appointment", yields no session.

Confidence rule as everywhere: nothing is invented. A schedule we can't read is
left as `status: "none"` and the page lists it under "no posted schedule".

Stdlib only. Tested in scripts/tests/test_market_schedule.py.
"""
from __future__ import annotations

import re
from datetime import date
from typing import List, Optional

DAYS = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7}
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

_MONTH_RE = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
             r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?")
_DAY_RE = (r"(?:mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?|"
           r"fri(?:day)?|sat(?:urday)?|sun(?:day)?)s?")
_TIME = r"(?:noon|\d{1,2}(?::\d{2})?\s*(?:[ap]\.?\s?m\.?)?)"
TIME_RANGE = re.compile(rf"(?P<a>{_TIME})\s*(?:-|–|—|to)\s*(?P<b>{_TIME}|dusk|sunset)",
                        re.I)
DAY_RANGE = re.compile(rf"\b(?P<a>{_DAY_RE})\s*(?:-|–|through|thru|to)\s*(?P<b>{_DAY_RE})\b", re.I)
DAY_WORD = re.compile(rf"\b{_DAY_RE}\b", re.I)
MONTH_DAY = re.compile(rf"\b(?P<m>{_MONTH_RE})\s*(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\b", re.I)
DATE_RANGE = re.compile(
    rf"\b(?P<m1>{_MONTH_RE})\s*(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?\s*(?:-|–|through|thru|to)\s*"
    rf"(?P<m2>{_MONTH_RE})?\s*(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\b", re.I)
MONTH_RANGE = re.compile(rf"\b(?P<a>{_MONTH_RE})\s*(?:-|–|through|thru|to)\s*(?P<b>{_MONTH_RE})(?!\s*\d)",
                         re.I)
# Wording that means a segment's days only happen on some unstated dates.
ONLY_SOME = re.compile(r"select dates|some dates|by appointment", re.I)
PAREN = re.compile(r"\(([^)]*)\)")
# Wording that means the regular pattern doesn't hold every week.
VAGUE = re.compile(r"alternat|select|some days|except|appointment|varies|closed|weather|"
                   r"season:|pop-?up|call", re.I)


def _month(tok: str) -> int:
    return MONTHS[tok.strip(". ").lower()[:3]]


def _day(tok: str) -> int:
    return DAYS[tok.lower()[:3]]


def _clock(tok: str, meridiem: Optional[str] = None):
    """'8:30 am' -> (8, 30, 'am'); meridiem may be missing (None)."""
    t = tok.strip().lower()
    if t == "noon":
        return 12, 0, "pm"
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap])?", t)
    h, mi, mer = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    return h, mi, (mer + "m") if mer else meridiem


def _to24(h: int, mi: int, mer: str) -> str:
    if mer == "pm" and h != 12:
        h += 12
    if mer == "am" and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}"


def parse_time_range(a: str, b: str):
    """Return (open, close, closeText). Fills in a missing am/pm the way people write
    it: '3:30 - 7:30 p.m.' is afternoon, '8 - 12:30' runs morning to midday."""
    close_text = None
    if b.lower() in ("dusk", "sunset"):
        close_text, bh = b.lower(), None
    else:
        bh, bm, bmer = _clock(b)
    ah, am_, amer = _clock(a)
    if bh is not None and bmer is None:
        bmer = "pm" if (bh == 12 or bh <= 7) else "am"
        if amer and amer == "pm" and bmer == "am":
            bmer = "pm"
    if amer is None:
        if bh is not None and bmer:
            amer = bmer
            # '10 - 2 pm' -> 10 am; '3:30 - 7:30 pm' -> 3:30 pm
            if _to24(ah, am_, amer) >= _to24(bh, bm, bmer):
                amer = "am"
        else:
            amer = "pm" if (ah == 12 or ah <= 6) else "am"
    open_ = _to24(ah, am_, amer)
    close = _to24(bh, bm, bmer) if bh is not None else None
    return open_, close, close_text


def parse_days(text: str) -> List[int]:
    t = text.lower()
    if re.search(r"\b(daily|every ?day|7 days)\b", t):
        return list(range(1, 8))
    days: List[int] = []
    for m in DAY_RANGE.finditer(text):
        a, b = _day(m.group("a")), _day(m.group("b"))
        span = list(range(a, b + 1)) if a <= b else list(range(a, 8)) + list(range(1, b + 1))
        days += span
    rest = DAY_RANGE.sub(" ", text)
    days += [_day(m.group(0)) for m in DAY_WORD.finditer(rest)]
    return sorted(set(days))


def _iso(year: int, month: int, day: int) -> Optional[str]:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _months_between(a: int, b: int) -> List[int]:
    return list(range(a, b + 1)) if a <= b else list(range(a, 13)) + list(range(1, b + 1))


def parse_season(text: str, year: int) -> dict:
    """Season facts stated in a bit of text: a date range, a month range, single
    months, or a list of one-off dates."""
    out = {"from": None, "to": None, "months": None, "dates": None}
    m = DATE_RANGE.search(text)
    if m:
        m1 = _month(m.group("m1"))
        m2 = _month(m.group("m2")) if m.group("m2") else m1
        y2 = year + 1 if (m2, int(m.group("d2"))) < (m1, int(m.group("d1"))) else year
        out["from"] = _iso(year, m1, int(m.group("d1")))
        out["to"] = _iso(y2, m2, int(m.group("d2")))
        return out
    dates = [_iso(year, _month(d.group("m")), int(d.group("d"))) for d in MONTH_DAY.finditer(text)]
    dates = [d for d in dates if d]
    if dates:
        out["dates"] = sorted(set(dates))
        return out
    months: List[int] = []
    for r in MONTH_RANGE.finditer(text):
        months += _months_between(_month(r.group("a")), _month(r.group("b")))
    rest = MONTH_RANGE.sub(" ", text)
    months += [_month(x) for x in re.findall(rf"\b{_MONTH_RE}(?=\W|$)", rest, re.I)
               if x.lower() not in ("mar", "may") or x[0].isupper()]
    if months:
        out["months"] = sorted(set(months))
    return out


def parse_months_open(value: str) -> List[int]:
    out = []
    for part in re.split(r"[,;]", value or ""):
        part = part.strip()
        if part:
            try:
                out.append(_month(part))
            except KeyError:
                pass
    return sorted(set(out))


def _segment_sessions(seg: str, inherited_days: List[int], year: int):
    """Sessions for one ';'-separated piece of the Hours text."""
    approx = bool(VAGUE.search(seg))
    ranges = list(TIME_RANGE.finditer(seg))
    # "8:00am - 2:00pm (some days to 3:00pm)": a time inside a vague aside isn't a session.
    ranges = [r for r in ranges
              if not any(p.start() < r.start() < p.end() and VAGUE.search(p.group(1))
                         for p in PAREN.finditer(seg))]
    if not ranges:
        return [], inherited_days, approx or bool(seg.strip())
    prefix = seg[:ranges[0].start()]
    days = parse_days(prefix) or parse_days(seg) or inherited_days
    if ONLY_SOME.search(prefix):
        # "Sat & Sun (select dates near July 4th)": not a weekly pattern we can place.
        return [], days, True
    sessions = []
    for i, r in enumerate(ranges):
        open_, close, close_text = parse_time_range(r.group("a"), r.group("b"))
        # Season words that belong to this time: everything after it up to the next
        # time; for the first one also anything in the day prefix.
        # A time that another time follows only owns a bracketed season right after
        # it ("8-12 (May-Sep.) 9-12 (Oct.)"); loose words between two times are a note.
        if i + 1 < len(ranges):
            nxt = PAREN.match(seg[r.end():ranges[i + 1].start()].lstrip())
            own = nxt.group(0) if nxt else ""
        else:
            own = seg[r.end():]
        own += " " + prefix if i == 0 else ""
        own = PAREN.sub(lambda p: "" if VAGUE.search(p.group(1)) else p.group(0), own)
        if VAGUE.search(own) and not PAREN.search(own):
            own = ""  # 'closed on July 4th' etc: a note, not a season
        season = parse_season(own, year)
        sessions.append({"days": [] if season["dates"] else days, "open": open_,
                         "close": close, "closeText": close_text, **season})
    if len(sessions) > 1 and not any(s["from"] or s["months"] or s["dates"] for s in sessions[1:]):
        # Two times with nothing telling them apart ("Summer: 9-1, Winter: 10-1").
        sessions, approx = sessions[:1], True
    return sessions, days, approx


def parse_schedule(hours: str, months_open: str = "", year: Optional[int] = None) -> dict:
    """Parse one market. Returns {status, approx, months, sessions}; status is
    'full', 'partial' (some text unreadable) or 'none'."""
    year = year or date.today().year
    months = parse_months_open(months_open)
    text = (hours or "").strip()
    result = {"status": "none", "approx": False, "months": months, "sessions": []}
    if not text:
        return result
    days: List[int] = []
    unreadable = False
    for seg in re.split(r";", text):
        if not seg.strip():
            continue
        sessions, days, approx = _segment_sessions(seg, days, year)
        result["sessions"] += sessions
        result["approx"] |= approx
        unreadable |= not sessions
    result["sessions"] = [s for s in result["sessions"] if s["days"] or s["dates"]]
    if result["sessions"]:
        result["status"] = "partial" if unreadable else "full"
    return result


if __name__ == "__main__":  # quick look: python scripts/market_schedule.py "Sat: 8-1" "June, July"
    import json
    import sys
    print(json.dumps(parse_schedule(*sys.argv[1:3]), indent=1))
