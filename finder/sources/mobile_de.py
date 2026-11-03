"""mobile.de

mobile.de uses its own internal codes for every make and model, and it is
known to protect itself strongly against automated browsers. So this source
works like this:

  1. You set up the search once in your own browser on mobile.de and paste
     that URL into config/profiles.toml under [profiles.search_urls].
  2. We open that URL, page by page, at human pace.
  3. If mobile.de shows a bot check, we stop and tell you to use its
     e-mail alerts instead. We never try to get around the check.

Reading the results: every ad on the page is a link to
".../details.html?id=<number>". We collect those links and read the price,
mileage and first-registration date from the text of each card.
"""

import re
from urllib.parse import urljoin

from finder.listing import Listing, to_int
from finder.sources.base import Source

PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d{3,6})\s*€")
KM_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d{1,6})\s*km\b")
FIRST_REG_RE = re.compile(r"\b(?:EZ\s*)?(\d{2}/\d{4})\b")
ID_RE = re.compile(r"[?&]id=(\d+)")
ZIP_CITY_RE = re.compile(r"\b([A-Z]{2})?-?(\d{4,5})\s+([A-ZÄÖÜ][\w\- .äöüß]+)")
FUEL_WORDS = ["Diesel", "Benzin", "Elektro", "Hybrid", "Autogas", "Erdgas"]


class MobileDe(Source):
    name = "mobile_de"
    email_alert_help = (
        "On mobile.de, set up the search by hand, click 'Suche speichern' "
        "and turn on e-mail notifications for new results."
    )
    page_param = "pageNumber"   # mobile.de calls the page number pageNumber

    def search_url(self, profile):
        custom = profile.search_urls.get(self.name, "").strip()
        if not custom:
            print(
                "    mobile.de needs a search URL. Open suchen.mobile.de in your browser,\n"
                "    set make, model, fuel, price, radius and 'Unfallfrei / nicht beschädigt',\n"
                "    click search, copy the address bar and paste it into\n"
                f"    config/profiles.toml under [profiles.search_urls] mobile_de for '{profile.name}'."
            )
            return None
        return custom

    def parse_results(self, page):
        listings = {}
        for link in page.query_selector_all("a[href*='details.html?id=']"):
            href = link.get_attribute("href") or ""
            match = ID_RE.search(href)
            if not match or match.group(1) in listings:
                continue
            text = (link.inner_text() or "").strip()
            if not text:
                continue
            listings[match.group(1)] = self._to_listing(match.group(1), urljoin(page.url, href), text)

        if not listings:
            self.save_debug_page(page, "no listing links found")
        return list(listings.values())

    def _to_listing(self, listing_id, url, text):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        price = PRICE_RE.search(text)
        km = KM_RE.search(text)
        first_reg = FIRST_REG_RE.search(text)
        place = ZIP_CITY_RE.search(text)
        fuel = next((word for word in FUEL_WORDS if word in text), None)
        title = next((line for line in lines if not PRICE_RE.search(line)), lines[0] if lines else "")
        return Listing(
            source=self.name,
            listing_id=listing_id,
            url=url.split("&")[0] if "details.html?id=" in url else url,
            title=title[:200],
            price_eur=to_int(price.group(1)) if price else None,
            mileage_km=to_int(km.group(1)) if km else None,
            first_registration=first_reg.group(1) if first_reg else None,
            fuel=fuel,
            location=place.group(0) if place else None,
            country=(place.group(1) or "DE") if place else None,
            raw={"card_text": text},
        )

