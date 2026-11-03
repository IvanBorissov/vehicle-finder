"""Tests for the paging rules in run.py, using a fake website.

No browser and no internet: FakeSite pretends to be a results site, and
each test says which listing ids appear on which page.

Run with:  python -m unittest
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from finder.listing import Listing
from finder.profiles import Profile, Settings
from finder.sources.base import Source
from finder.storage import Storage
from run import run_search

SEARCH_URL = "https://example.test/search?model=caddy"
PROFILE = Profile(name="test", make="VW", model="Caddy", max_price_eur=10000, fuel="diesel")


class FakeSite(Source):
    """A pretend site. pages = {page number: [listing ids on that page]}."""
    name = "fake"

    def __init__(self, pages):
        self.pages = pages

    def search_url(self, profile):
        return SEARCH_URL

    def parse_results(self, page_url):
        number = int(page_url.split("page=")[1])
        return [
            Listing(source=self.name, listing_id=i, url=f"https://example.test/{i}",
                    title=f"VW Caddy {i}", price_eur=5000)
            for i in self.pages.get(number, [])
        ]


class FakeBrowser:
    """Remembers which pages were opened, in order."""

    def __init__(self):
        self.opened = []

    def open(self, url):
        self.opened.append(int(url.split("page=")[1]))
        return url


class TestPaging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.tmp.name) / "test.db")

    def tearDown(self):
        self.storage.db.close()
        self.tmp.cleanup()

    def already_have(self, *ids):
        """Pretend an earlier run already saved these listings."""
        for i in ids:
            self.storage.save("test", Listing(source="fake", listing_id=i, url="", title=f"VW Caddy {i}",
                                               price_eur=5000), None)

    def run_it(self, pages, budget=60, page_cap=8):
        settings = Settings(max_listings_per_run=budget, max_pages_per_run=page_cap)
        browser = FakeBrowser()
        with contextlib.redirect_stdout(io.StringIO()):   # keep test output quiet
            counts = run_search(browser, self.storage, settings, PROFILE, FakeSite(pages))
        return counts, browser.opened

    def progress(self):
        return self.storage.get_progress("test", "fake", SEARCH_URL)

    def test_promoted_ad_counts_once(self):
        counts, opened = self.run_it({1: ["promo", "a", "b"], 2: ["promo", "c"], 3: ["promo"]})
        self.assertEqual(counts["new"], 3 + 1)            # promo, a, b, c
        self.assertEqual(counts["seen before"], 0)        # promo was not "seen before"
        self.assertEqual(opened, [1, 2, 3])               # page 3 had only a repeat: the end
        self.assertEqual(self.progress(), (3, True))

    def test_budget_counts_only_new_listings(self):
        self.already_have("old1", "old2")
        counts, opened = self.run_it({1: ["n1", "old1", "old2"], 2: ["n2", "n3", "n4"]}, budget=3)
        self.assertEqual(counts["new"], 3)
        self.assertEqual(counts["seen before"], 2)
        self.assertEqual(opened, [1, 2])
        self.assertEqual(self.progress(), (2, False))     # carry on from page 2 next time

    def test_jumps_to_where_last_run_stopped(self):
        self.already_have("old1")
        self.storage.set_progress("test", "fake", SEARCH_URL, 5, False)
        counts, opened = self.run_it({1: ["n1", "old1"], 5: ["deep1", "deep2"], 6: []})
        self.assertEqual(opened, [1, 5, 6])               # pages 2-4 skipped
        self.assertEqual(counts["new"], 3)
        self.assertEqual(self.progress(), (6, True))      # page 6 was empty: complete

    def test_complete_search_only_checks_first_pages(self):
        self.already_have("old1")
        self.storage.set_progress("test", "fake", SEARCH_URL, 9, True)
        counts, opened = self.run_it({1: ["n1"], 2: ["n2", "old1"], 3: ["n3"]})
        self.assertEqual(opened, [1, 2])                  # stops at the first known listing
        self.assertEqual(counts["new"], 2)
        self.assertEqual(self.progress(), (9, True))      # stays complete

    def test_page_safety_cap(self):
        pages = {n: [f"p{n}a", f"p{n}b"] for n in range(1, 21)}
        counts, opened = self.run_it(pages, budget=1000, page_cap=8)
        self.assertEqual(opened, list(range(1, 9)))
        self.assertEqual(self.progress(), (9, False))     # next run goes on from page 9

    def test_saved_place_never_moves_back(self):
        self.storage.set_progress("test", "fake", SEARCH_URL, 6, False)
        # Lots of new ads at the top fill the budget on page 1, before any jump.
        self.run_it({1: ["n1", "n2", "n3"]}, budget=2)
        self.assertEqual(self.progress(), (6, False))

    def test_changed_search_starts_over(self):
        self.storage.set_progress("test", "fake", "https://example.test/search?model=OTHER", 5, True)
        self.assertEqual(self.progress(), (1, False))


if __name__ == "__main__":
    unittest.main()
