"""What every source (website) must provide."""

from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from finder.listing import Listing


class Source:
    name = "base"
    # Shown when the site blocks us, so you know the manual fallback.
    email_alert_help = ""
    # The name the site uses for the page number in its URLs.
    page_param = "page"

    def search_url(self, profile) -> str | None:
        """Return the URL of the first results page, or None if we cannot build one."""
        raise NotImplementedError

    def page_url(self, search_url: str, page_number: int) -> str:
        """Return the same search URL, but for result page <page_number>."""
        parts = urlparse(search_url)
        query = parse_qs(parts.query)
        query[self.page_param] = [str(page_number)]
        return urlunparse(parts._replace(query=urlencode(query, doseq=True)))

    def parse_results(self, page) -> list[Listing]:
        """Read listings out of a loaded Playwright page."""
        raise NotImplementedError

    def save_debug_page(self, page, reason: str) -> Path:
        """Save the page HTML so we can see what went wrong."""
        folder = Path("debug")
        folder.mkdir(exist_ok=True)
        path = folder / f"{self.name}-{datetime.now():%Y%m%d-%H%M%S}.html"
        path.write_text(page.content(), encoding="utf-8")
        print(f"    saved the page to {path} ({reason})")
        return path
