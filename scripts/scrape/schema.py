"""Normalized schema for the Colorado farmers-market scrape.

Every source is mapped into a `Market` record whose public columns are exactly the
22 My Maps columns that the Colorado Proud / Farm Fresh pipeline emits
(see scripts/fetch_farm_data.py and DATA.md). This lets the output import into the
same Google My Maps setup with no changes.

Confidence rule: a field is only ever populated when a source *states it explicitly*.
Nothing is inferred or guessed. Every populated field records which source it came
from in `.provenance`, so conflicts and coverage can be audited later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# The 22 output columns, in the exact order fetch_farm_data.py writes them.
COLUMNS = [
    "Business Name", "Category", "Address", "City", "County", "State", "Zip",
    "Phone", "Call first?", "Website", "Email", "Facebook", "Instagram",
    "Hours", "Months Open", "Products", "Certified Organic", "SNAP",
    "ADA Accessible", "Notes", "Latitude", "Longitude",
]

# Fields that may carry a source label in `provenance`. (State/Category are constant
# for this project, and Latitude/Longitude provenance is tracked via `geo_source`.)
PROVENANCED = [
    "Business Name", "Address", "City", "County", "Zip", "Phone", "Website",
    "Email", "Facebook", "Instagram", "Hours", "Months Open", "Products",
    "Certified Organic", "SNAP", "ADA Accessible", "Notes",
]


@dataclass
class Market:
    """One farmers market, normalized. All string fields default to "" (not None) so
    CSV output is clean and merge logic can treat "" uniformly as 'missing'."""

    business_name: str = ""
    category: str = "Farmers' Market"   # constant for this project
    address: str = ""
    city: str = ""
    county: str = ""
    state: str = "CO"
    zip: str = ""
    phone: str = ""
    call_first: str = ""
    website: str = ""
    email: str = ""
    facebook: str = ""
    instagram: str = ""
    hours: str = ""
    months_open: str = ""
    products: str = ""
    certified_organic: str = ""
    snap: str = ""
    ada_accessible: str = ""
    notes: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Bookkeeping (not written to the My Maps CSV, but kept in the raw CSV).
    source: str = ""                 # primary source that created this record
    geo_source: str = ""             # "source" | "census-geocoder" | "" (none)
    dup_hint: str = ""               # name of a suspected duplicate, for human review
    provenance: dict = field(default_factory=dict)   # column -> source label

    def set(self, attr: str, value, source: str) -> None:
        """Set a field only if `value` is non-empty and the field is currently
        empty; record provenance. Enforces the explicit-only confidence rule and
        makes 'first source wins' the default merge behavior for a single field."""
        if value is None:
            return
        value = value.strip() if isinstance(value, str) else value
        if value == "" or value == []:
            return
        current = getattr(self, attr)
        if current in ("", None):
            setattr(self, attr, value)
            col = ATTR_TO_COLUMN.get(attr)
            if col in PROVENANCED:
                self.provenance[col] = source

    def to_mymaps_row(self) -> dict:
        return {
            "Business Name": self.business_name,
            "Category": self.category,
            "Address": self.address,
            "City": self.city,
            "County": self.county,
            "State": self.state,
            "Zip": self.zip,
            "Phone": self.phone,
            "Call first?": self.call_first,
            "Website": self.website,
            "Email": self.email,
            "Facebook": self.facebook,
            "Instagram": self.instagram,
            "Hours": self.hours,
            "Months Open": self.months_open,
            "Products": self.products,
            "Certified Organic": self.certified_organic,
            "SNAP": self.snap,
            "ADA Accessible": self.ada_accessible,
            "Notes": self.notes,
            "Latitude": "" if self.latitude is None else self.latitude,
            "Longitude": "" if self.longitude is None else self.longitude,
        }


# attribute name -> output column label (for provenance bookkeeping)
ATTR_TO_COLUMN = {
    "business_name": "Business Name", "address": "Address", "city": "City",
    "county": "County", "zip": "Zip", "phone": "Phone", "website": "Website",
    "email": "Email", "facebook": "Facebook", "instagram": "Instagram",
    "hours": "Hours", "months_open": "Months Open", "products": "Products",
    "certified_organic": "Certified Organic", "snap": "SNAP",
    "ada_accessible": "ADA Accessible", "notes": "Notes",
}
