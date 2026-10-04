"""Offline tests for scripts/market_schedule.py (Hours text -> calendar sessions).

Cases are real Hours strings from the Phase 2 market data. Run:
python -m pytest scripts/tests -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_schedule import parse_schedule, parse_time_range  # noqa: E402

SAT, SUN, MON, WED, THU, FRI = 6, 7, 1, 3, 4, 5


def brief(hours, months="", year=2026):
    r = parse_schedule(hours, months, year)
    return r, [(s["days"], s["open"], s["close"]) for s in r["sessions"]]


@pytest.mark.parametrize("a,b,exp", [
    ("8 am", "1:30 pm", ("08:00", "13:30", None)),
    ("3:30", "7:30 p.m.", ("15:30", "19:30", None)),   # am/pm only on the close
    ("10", "2", ("10:00", "14:00", None)),             # no am/pm at all
    ("8", "12:30", ("08:00", "12:30", None)),
    ("7:30am", "Noon", ("07:30", "12:00", None)),
    ("5:30pm", "dusk", ("17:30", None, "dusk")),
    ("5", "7:30PM", ("17:00", "19:30", None)),
    ("4", "8pm", ("16:00", "20:00", None)),
    ("12:00pm", "6:00pm", ("12:00", "18:00", None)),
])
def test_time_ranges(a, b, exp):
    assert parse_time_range(a, b) == exp


@pytest.mark.parametrize("hours,days", [
    ("Sat: 9:00am - 1:00pm", [SAT]),
    ("Sunday 9:00 AM - 2:00 PM", [SUN]),
    ("Saturday 8AM-1PM", [SAT]),
    ("Fri, Sat: 9:00am - 1:00pm", [FRI, SAT]),
    ("Sat-Sun: 12:00pm - 6:00pm", [SAT, SUN]),
    ("Mon-Sun: 9:00am - 6:00pm", list(range(1, 8))),
    ("Daily: 10:00am - 6:00pm", list(range(1, 8))),
])
def test_days(hours, days):
    r, sessions = brief(hours)
    assert r["status"] == "full" and sessions[0][0] == days


def test_two_markets_a_week():
    r, s = brief("Wed: 3:30 - 7:30 p.m.; Sat: 8:00 a.m. - 2:00 p.m.")
    assert s == [([WED], "15:30", "19:30"), ([SAT], "08:00", "14:00")]


def test_stated_date_ranges_win_over_months():
    r = parse_schedule("Sat: 8:30am - 2:00pm (Jun 6 - Sep 4); Sat: 9:00am - 2:00pm (Sep 5 - Oct 3)",
                       "June, July, August, September, October", 2026)
    a, b = r["sessions"]
    assert (a["from"], a["to"], a["open"]) == ("2026-06-06", "2026-09-04", "08:30")
    assert (b["from"], b["to"], b["open"]) == ("2026-09-05", "2026-10-03", "09:00")
    assert r["months"] == [6, 7, 8, 9, 10]


def test_month_range_per_time():
    r = parse_schedule("Sat: 8 AM - 12 PM (May-Sep.) 9 AM - 12 PM (Oct.)", "", 2026)
    assert [(s["open"], s["months"]) for s in r["sessions"]] == [
        ("08:00", [5, 6, 7, 8, 9]), ("09:00", [10])]


def test_winter_wraps_the_year():
    r = parse_schedule("Sat: 9:00am - 1:00pm (June-September); Sat: 10:00am - 12:00pm (October-May)",
                       "", 2026)
    assert r["sessions"][1]["months"] == [1, 2, 3, 4, 5, 10, 11, 12]


def test_session_months_only_with_its_time():
    r = parse_schedule("Sat: 8:30am - 1:00pm; Wed: 8:30am - 1:00pm (June-August only)", "May", 2026)
    assert [s["months"] for s in r["sessions"]] == [None, [6, 7, 8]]


def test_one_off_dates():
    r = parse_schedule("Sat: 7:30am - Noon  May 16  June 6    July 18    October 3", "", 2026)
    (s,) = r["sessions"]
    assert s["dates"] == ["2026-05-16", "2026-06-06", "2026-07-18",
                          "2026-10-03"]
    assert s["days"] == []


def test_named_event_dates():
    r = parse_schedule("Frederick in Flight (Jun 27): 5:00pm - 9:00pm; "
                       "Miners Day (Sep 19): 11:00am - 4:00pm", "", 2026)
    assert [(s["dates"], s["open"]) for s in r["sessions"]] == [
        (["2026-06-27"], "17:00"), (["2026-09-19"], "11:00")]


def test_written_out_date_range_and_closed_note():
    r = parse_schedule("Sat: 9am - 2pm, Saturdays  June 20th through September 12th "
                       "(Closed on July 4th)", "", 2026)
    (s,) = r["sessions"]
    assert (s["from"], s["to"]) == ("2026-06-20", "2026-09-12")
    assert r["approx"] and s["dates"] is None


def test_loose_note_between_times_is_not_a_season():
    r, s = brief("Sat: 9 am - 1pm and October fest is 10 am - 3 pm")
    assert s == [([SAT], "09:00", "13:00")] and r["sessions"][0]["months"] is None
    assert r["approx"]


def test_vague_aside_is_not_a_session():
    r, s = brief("Fri: 8:00am - 2:00pm (some days to 3:00pm); "
                 "Sat & Sun (select dates near July 4th): 8:00am - 2:00pm")
    assert s == [([FRI], "08:00", "14:00")]
    assert r["approx"] and r["status"] == "partial"


@pytest.mark.parametrize("hours", ["Saturdays (alternating), 9 a.m. - 2 p.m.",
                                   "Sat: Summer Season: 9 am - 1 pm, Winter Season: 10 am - 1 pm",
                                   "Sat: 7:30am - Noon, except for select Eastside Pop-ups"])
def test_irregular_patterns_are_flagged(hours):
    r, s = brief(hours)
    assert r["approx"] and len(s) == 1


@pytest.mark.parametrize("hours", ["", "Mon: By appointment; Sat: By appointment"])
def test_nothing_readable(hours):
    r, s = brief(hours, "May, June")
    assert r["status"] == "none" and s == [] and r["months"] == [5, 6]
