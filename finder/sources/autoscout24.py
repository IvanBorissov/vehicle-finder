"""AutoScout24 (autoscout24.de).

How it works: the results page is built with Next.js, which puts all the
listing data as JSON inside a <script id="__NEXT_DATA__"> tag. We read that
JSON instead of scraping the visible text, which is far more reliable.
"""

import json
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from finder.listing import Listing, to_int
from finder.sources.base import Source

BASE = "https://www.autoscout24.de"

# AutoScout24's own codes.
FUEL_CODES = {"diesel": "D", "petrol": "B", "electric": "E", "hybrid": "2", "lpg": "L"}
COUNTRY_CODES = {"DE": "D", "AT": "A", "BE": "B", "ES": "E", "FR": "F", "IT": "I", "LU": "L", "NL": "NL"}
MAKE_SLUGS = {"vw": "volkswagen"}


def _dig(data, *keys, default=None):
    """Safely walk nested dicts: _dig(d, 'a', 'b') is d['a']['b'] or default."""
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


class AutoScout24(Source):
    name = "autoscout24"
    email_alert_help = (
        "On autoscout24.de, set up the search by hand, click 'Suche speichern' "
        "(save search) and turn on e-mail alerts."
    )

    def search_page_urls(self, profile, max_pages):
        custom = profile.search_urls.get(self.name, "").strip()
        if custom:
            return [_with_page(custom, n) for n in range(1, max_pages + 1)]

        make = MAKE_SLUGS.get(profile.make.lower(), profile.make.lower())
        model = profile.model.lower().replace(" ", "-")
        countries = [COUNTRY_CODES[c] for c in profile.countries if c in COUNTRY_CODES]
        params = {
            "atype": "C",                       # cars
            "ustate": "N,U",                    # new and used
            "priceto": profile.max_price_eur,
            "zip": profile.center_zip,
            "lat": profile.center_lat,
            "lon": profile.center_lon,
            "zipr": profile.radius_km,
            "cy": ",".join(countries) or "D",
            "sort": "age",                      # newest first
            "desc": 1,
        }
        if profile.fuel in FUEL_CODES:
            params["fuel"] = FUEL_CODES[profile.fuel]
        if profile.must_be_drivable:
            params["damaged_listing"] = "exclude"   # site's own damage filter
        first = f"{BASE}/lst/{make}/{model}?{urlencode(params)}"
        return [_with_page(first, n) for n in range(1, max_pages + 1)]

    def parse_results(self, page):
        script = page.query_selector("script#__NEXT_DATA__")
        if script is None:
            self.save_debug_page(page, "no __NEXT_DATA__ found")
            return []
        data = json.loads(script.inner_text())
        raw_listings = _dig(data, "props", "pageProps", "listings", default=[]) or []
        return [self._to_listing(item) for item in raw_listings if item.get("id")]

    def _to_listing(self, item):
        vehicle = item.get("vehicle", {}) or {}
        tracking = item.get("tracking", {}) or {}
        location = item.get("location", {}) or {}
        seller = item.get("seller", {}) or {}

        title = " ".join(
            part for part in [vehicle.get("make"), vehicle.get("model"), vehicle.get("modelVersionInput")] if part
        )
        price = to_int(tracking.get("price")) or to_int(_dig(item, "price", "priceFormatted"))
        mileage = to_int(tracking.get("mileage")) or to_int(vehicle.get("mileageInKm"))
        place = " ".join(p for p in [location.get("countryCode"), location.get("zip"), location.get("city")] if p)
        url = item.get("url", "")
        if url.startswith("/"):
            url = BASE + url

        return Listing(
            source=self.name,
            listing_id=str(item["id"]),
            url=url,
            title=title or "(no title)",
            price_eur=price,
            mileage_km=mileage,
            first_registration=tracking.get("firstRegistration"),
            fuel=vehicle.get("fuel"),
            location=place or None,
            country=location.get("countryCode"),
            seller=seller.get("companyName") or seller.get("type"),
            raw=item,
        )


def _with_page(url, page_number):
    """Return the same URL with page=<n> set."""
    parts = urlparse(url)
    query = parse_qs(parts.query)
    query["page"] = [str(page_number)]
    return urlunparse(parts._replace(query=urlencode(query, doseq=True)))
