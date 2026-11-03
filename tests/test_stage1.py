"""Tests that run offline on small hand-made pages in tests/pages/.

Run with:  python -m unittest
"""

import tempfile
import unittest
from pathlib import Path

from finder.browser import PoliteBrowser, SiteBlocked
from finder.filters import check_listing
from finder.listing import to_int
from finder.profiles import Profile, Settings, load_config
from finder.sources.autoscout24 import AutoScout24
from finder.sources.mobile_de import MobileDe
from finder.storage import Storage

PAGES = Path(__file__).parent / "pages"
SETTINGS = Settings(pause_seconds=(0, 0), not_drivable_words=["motorschaden", "bastler"])
PROFILE = Profile(name="test", make="VW", model="Caddy", max_price_eur=10000, fuel="diesel")


def open_sample(browser, name):
    return browser.open((PAGES / name).resolve().as_uri())


class TestStage1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = PoliteBrowser(SETTINGS).__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.browser.__exit__(None, None, None)

    def test_config_file_loads(self):
        settings, profiles = load_config("config/profiles.toml")
        self.assertTrue(profiles)
        self.assertGreater(settings.max_listings_per_run, 0)

    def test_to_int(self):
        self.assertEqual(to_int("€ 8.990,-"), 8990)
        self.assertEqual(to_int("145.000 km"), 145000)
        self.assertIsNone(to_int(None))

    def test_autoscout24_parsing_and_filters(self):
        listings = AutoScout24().parse_results(open_sample(self.browser, "autoscout24_sample.html"))
        self.assertEqual(len(listings), 3)
        first = listings[0]
        self.assertEqual(first.price_eur, 8990)
        self.assertEqual(first.mileage_km, 145000)
        self.assertTrue(first.url.startswith("https://www.autoscout24.de/angebote/"))
        reasons = [check_listing(l, PROFILE, SETTINGS) for l in listings]
        self.assertIsNone(reasons[0])
        self.assertIn("motorschaden", reasons[1])
        self.assertIn("over budget", reasons[2])

    def test_mobile_de_parsing_and_filters(self):
        listings = MobileDe().parse_results(open_sample(self.browser, "mobile_de_sample.html"))
        self.assertEqual([l.listing_id for l in listings], ["401", "402"])
        self.assertEqual(listings[0].price_eur, 7450)
        self.assertEqual(listings[0].mileage_km, 178000)
        self.assertEqual(listings[0].first_registration, "08/2015")
        self.assertIsNone(check_listing(listings[0], PROFILE, SETTINGS))
        self.assertIn("bastler", check_listing(listings[1], PROFILE, SETTINGS))

    def test_blocked_page_stops(self):
        with self.assertRaises(SiteBlocked):
            open_sample(self.browser, "blocked_sample.html")

    def test_storage_remembers_listings(self):
        listing = AutoScout24().parse_results(open_sample(self.browser, "autoscout24_sample.html"))[0]
        with tempfile.TemporaryDirectory() as tmp:
            storage = Storage(Path(tmp) / "test.db")
            self.assertEqual(storage.save("test", listing, None), "new")
            self.assertEqual(storage.save("test", listing, None), "seen before")
            listing.price_eur = 8500
            self.assertEqual(storage.save("test", listing, None), "price changed")
            row = storage.accepted("test")[0]
            self.assertEqual((row["price_eur"], row["previous_price_eur"], row["times_seen"]), (8500, 8990, 3))


if __name__ == "__main__":
    unittest.main()
