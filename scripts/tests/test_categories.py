"""Every Category label in the Phase 2 output must roll up into a map filter group."""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scrape import categories

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_groups_for_multi_label_and_badges():
    assert categories.groups_for("Agritourism, On-Farm / Ranch Sales, Sells to Schools") == \
        ["agritourism", "farms"]
    assert categories.groups_for("Bakery") == ["shops"]
    assert categories.groups_for("Community Food Hub") == ["assistance"]


def test_no_label_is_left_without_a_group():
    path = os.path.join(REPO, "source-data", "phase2", "co_farmers_markets_all_raw.csv")
    with open(path, encoding="utf-8-sig") as fh:
        cats = [r["Category"] for r in csv.DictReader(fh)]
    assert categories.unknown_labels(cats) == []      # add new labels to GROUPS/BADGES
    assert "Other" not in {c.strip() for cat in cats for c in cat.split(",")}
