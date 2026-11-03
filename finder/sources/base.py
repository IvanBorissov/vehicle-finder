"""What every source (website) must provide."""

from pathlib import Path
from datetime import datetime

from finder.listing import Listing


class Source:
    name = "base"
    # Shown when the site blocks us, so you know the manual fallback.
    email_alert_help = ""

    def search_page_urls(self, profile, max_pages: int) -> list[str]:
        """Return the result-page URLs to visit (page 1, 2, 3, ...)."""
        raise NotImplementedError

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
