"""Deduplicate + merge markets across sources into one row per real market.

Priority: sources are folded in the order given (put the most trustworthy first —
Colorado Proud, then USDA, then CFMA, then curated). The first source to fill a
field wins; later sources only fill gaps. Provenance is preserved per field.

Dedup key: normalized-name + city. A light second pass also merges two groups whose
coordinates sit within ~200 m of each other (catches name spelling drift), so long
as they are in the same city.
"""
from __future__ import annotations

import math
from typing import Dict, List

from .normalize import name_key
from .schema import ATTR_TO_COLUMN, Market

MERGE_METERS = 200


def _haversine_m(a: Market, b: Market) -> float:
    if None in (a.latitude, a.longitude, b.latitude, b.longitude):
        return math.inf
    r = 6371000.0
    p1, p2 = math.radians(a.latitude), math.radians(b.latitude)
    dp = math.radians(b.latitude - a.latitude)
    dl = math.radians(b.longitude - a.longitude)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _fold(base: Market, other: Market) -> None:
    """Fill base's empty fields from other, carrying other's provenance."""
    for attr, col in ATTR_TO_COLUMN.items():
        if getattr(base, attr) in ("", None) and getattr(other, attr) not in ("", None):
            setattr(base, attr, getattr(other, attr))
            base.provenance[col] = other.provenance.get(col, other.source)
    if base.latitude is None and other.latitude is not None:
        base.latitude, base.longitude = other.latitude, other.longitude
        base.geo_source = other.geo_source or other.source
    if other.source and other.source not in base.source.split("+"):
        base.source = f"{base.source}+{other.source}" if base.source else other.source


def flag_possible_dups(markets: List[Market], radius_m: int = 150) -> None:
    """Non-destructive: set m.dup_hint to a sibling's name when two markets in the
    same city look like the same place — one name is a token-subset of the other
    (the strong signal), or they sit almost on top of each other (<= radius_m).
    Surfaced for human review, NOT merged — auto-merging would wrongly collapse
    distinct seasonal / East-West listings that share a name stem."""
    for i, a in enumerate(markets):
        for b in markets[i + 1:]:
            if a.city.strip().lower() != b.city.strip().lower():
                continue
            ta = set(name_key(a.business_name).split())
            tb = set(name_key(b.business_name).split())
            subset = ta and tb and (ta <= tb or tb <= ta)
            close = _haversine_m(a, b) <= radius_m
            if subset or close:
                a.dup_hint = a.dup_hint or b.business_name
                b.dup_hint = b.dup_hint or a.business_name


def merge(records: List[Market]) -> List[Market]:
    """Fold an ordered list of records (highest priority first) into unique markets."""
    groups: Dict[tuple, Market] = {}
    for rec in records:
        key = (name_key(rec.business_name), rec.city.strip().lower())
        if key in groups:
            _fold(groups[key], rec)
            continue
        # second-chance merge on coordinate proximity within the same city
        merged = False
        for (nk, city), base in groups.items():
            if city == key[1] and _haversine_m(base, rec) <= MERGE_METERS:
                _fold(base, rec)
                merged = True
                break
        if not merged:
            groups[key] = rec
    return list(groups.values())
