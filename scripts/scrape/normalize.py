"""Small, dependency-free normalization + validation helpers shared by all sources."""
from __future__ import annotations

import re

# Colorado bounding box (generous), used to sanity-check coordinates.
CO_LAT = (36.9, 41.1)
CO_LON = (-109.2, -101.9)


def pipes(s: str) -> str:
    """Turn a pipe-delimited source value into a clean comma-joined string."""
    return ", ".join(p.strip() for p in (s or "").split("|") if p.strip())


def phone(s: str) -> str:
    """Normalize a US phone to (XXX) XXX-XXXX. Returns '' if not 10 digits."""
    digits = re.sub(r"\D", "", s or "")
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10:
        return ""
    return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"


def zipcode(s: str) -> str:
    """Return a 5-digit zip, or '' if not recoverable."""
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", s or "")
    return m.group(1) if m else ""


def clean_url(s: str) -> str:
    """Add scheme if missing; return '' for junk. Does not validate reachability."""
    s = (s or "").strip()
    if not s or s.lower() in ("n/a", "na", "none", "-"):
        return ""
    if not re.match(r"^https?://", s, re.I):
        if "." not in s:
            return ""
        s = "https://" + s
    return s


def name_key(name: str) -> str:
    """Collapse a market name to a comparison key: lowercase, strip punctuation and
    common filler words so 'Pueblo Farmers Market' == 'Pueblo Farmers' Market'."""
    s = (name or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    stop = {"farmers", "farmer", "market", "markets", "the", "at", "of", "co",
            "colorado", "downtown", "community", "inc", "llc"}
    toks = [t for t in s.split() if t and t not in stop]
    return " ".join(sorted(toks)) if toks else re.sub(r"\s+", " ", s).strip()


def in_colorado(lat, lon) -> bool:
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return CO_LAT[0] <= lat <= CO_LAT[1] and CO_LON[0] <= lon <= CO_LON[1]


def titlecase(s: str) -> str:
    """Title-case an ALL-CAPS source value ('1522 CALIFORNIA ST' -> '1522 California St')
    without mangling numbers. Leaves already-mixed-case strings alone."""
    s = (s or "").strip()
    if not s or s != s.upper():   # only touch strings that are all-caps
        return s
    return " ".join(w.capitalize() for w in s.split())


def yesno(s: str) -> str:
    """Normalize assorted truthy/falsy source values to 'Yes'/'No'/''."""
    v = (s or "").strip().lower()
    if v in ("yes", "y", "true", "1", "accepted", "available"):
        return "Yes"
    if v in ("no", "n", "false", "0", "not accepted", "unavailable"):
        return "No"
    return ""
