"""The common shape of a listing, whatever site it came from."""

import re
from dataclasses import dataclass, field


@dataclass
class Listing:
    source: str            # "autoscout24", "mobile_de", ...
    listing_id: str        # the site's own id for the ad
    url: str
    title: str
    price_eur: int | None = None
    mileage_km: int | None = None
    first_registration: str | None = None   # e.g. "05/2015"
    fuel: str | None = None
    location: str | None = None              # e.g. "DE-60311 Frankfurt"
    country: str | None = None
    seller: str | None = None
    raw: dict = field(default_factory=dict)  # everything the site gave us


def to_int(text) -> int | None:
    """Turn '€ 8.990,-' or '123.456 km' or 8990 into 8990 / 123456."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return int(text)
    digits = re.sub(r"[^\d]", "", str(text).split(",")[0])
    return int(digits) if digits else None
