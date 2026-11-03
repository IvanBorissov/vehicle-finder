"""A small wrapper around Playwright that browses at a human pace.

Rules this file enforces:
  * a random pause before every page load (no rapid-fire requests);
  * one page at a time, in a normal Chromium browser;
  * if a site shows a captcha, a "bot check" or "access denied", we STOP.
    We never try to get around those checks.
"""

import os
import random
import time

from playwright.sync_api import sync_playwright

# Text that usually means "the site thinks you are a bot". Checked in lower case.
BLOCK_MARKERS = [
    "captcha",
    "are you a human",
    "access denied",
    "zugriff verweigert",
    "unusual traffic",
    "ungewöhnlichen datenverkehr",
    "checking your browser",
    "cf-challenge",
    "please verify you are human",
    "request blocked",
]


class SiteBlocked(Exception):
    """The site refused automated access. The search for this site stops."""


class PoliteBrowser:
    """Use with `with PoliteBrowser(settings) as browser:`."""

    def __init__(self, settings):
        self.settings = settings
        self._first_load = True

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=not self.settings.show_browser,
            # Normally empty. Only set CHROMIUM_PATH if you want a specific Chromium.
            executable_path=os.environ.get("CHROMIUM_PATH") or None,
        )
        self._context = self._browser.new_context(locale="de-DE", viewport={"width": 1366, "height": 900})
        self.page = self._context.new_page()
        return self

    def __exit__(self, *exc):
        self._context.close()
        self._browser.close()
        self._pw.stop()

    def pause(self):
        low, high = self.settings.pause_seconds
        seconds = random.uniform(low, high)
        print(f"    (waiting {seconds:.0f}s, human pace)")
        time.sleep(seconds)

    def open(self, url: str):
        """Load a page and return the Playwright page. Raises SiteBlocked."""
        if not self._first_load:
            self.pause()
        self._first_load = False

        response = self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        # Give the page a moment to finish building itself, like a person reading.
        self.page.wait_for_timeout(random.randint(1500, 3000))

        status = response.status if response else 0
        if status in (403, 429):
            raise SiteBlocked(f"HTTP {status} from {url}")

        title = (self.page.title() or "").lower()
        body = (self.page.inner_text("body") or "").lower()
        # A real results page has lots of text. A block page is short, so we
        # only look for block words in the body when the page is short.
        # (This avoids false alarms from cookie banners that mention "reCAPTCHA".)
        short_page = len(body) < 4000
        for marker in BLOCK_MARKERS:
            if marker in title or (short_page and marker in body):
                raise SiteBlocked(f"page shows '{marker}' at {url}")
        return self.page
