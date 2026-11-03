"""Run all enabled search profiles and save the results.

Usage:
    python run.py                         # every enabled profile, every site
    python run.py --profile caddy-diesel-frankfurt
    python run.py --source autoscout24    # only one site
    python run.py --dry-run               # only print the URLs, load nothing
"""

import argparse

from finder.browser import PoliteBrowser, SiteBlocked
from finder.filters import check_listing
from finder.profiles import load_config
from finder.sources import SOURCES
from finder.storage import Storage


def run_search(browser, storage, settings, profile, source):
    urls = source.search_page_urls(profile, settings.max_pages_per_search)
    counts = {"new": 0, "price changed": 0, "seen before": 0, "rejected": 0}
    handled = 0

    for page_number, url in enumerate(urls, start=1):
        print(f"  page {page_number}: {url}")
        page = browser.open(url)          # may raise SiteBlocked
        listings = source.parse_results(page)
        print(f"    found {len(listings)} listings on this page")
        if not listings:
            break                          # no more results (or the page changed)

        for listing in listings:
            reason = check_listing(listing, profile, settings)
            result = storage.save(profile.name, listing, reason)
            if reason:
                counts["rejected"] += 1
            else:
                counts[result] += 1
                if result == "new":
                    price = f"€{listing.price_eur:,}" if listing.price_eur else "no price"
                    print(f"    NEW  {listing.title} | {price} | {listing.mileage_km or '?'} km | {listing.location or ''}")
            handled += 1
            if handled >= settings.max_listings_per_run:
                print(f"    reached the limit of {settings.max_listings_per_run} listings for this run")
                return counts
    return counts


def main():
    parser = argparse.ArgumentParser(description="Find vehicles that match your profiles.")
    parser.add_argument("--config", default="config/profiles.toml")
    parser.add_argument("--profile", help="run only this profile (by name)")
    parser.add_argument("--source", choices=sorted(SOURCES), help="run only this site")
    parser.add_argument("--dry-run", action="store_true", help="print URLs without loading them")
    args = parser.parse_args()

    settings, profiles = load_config(args.config)
    if args.profile:
        profiles = [p for p in profiles if p.name == args.profile]
        if not profiles:
            raise SystemExit(f"No enabled profile called '{args.profile}'.")

    if args.dry_run:
        for profile in profiles:
            for source_name in profile.sources:
                if args.source and source_name != args.source:
                    continue
                print(f"[{profile.name}] {source_name}")
                for url in SOURCES[source_name]().search_page_urls(profile, settings.max_pages_per_search):
                    print("  ", url)
        return

    storage = Storage(settings.database)
    with PoliteBrowser(settings) as browser:
        for profile in profiles:
            for source_name in profile.sources:
                if args.source and source_name != args.source:
                    continue
                source = SOURCES[source_name]()
                print(f"\n[{profile.name}] searching {source_name}")
                try:
                    counts = run_search(browser, storage, settings, profile, source)
                    print(f"  done: {counts}")
                except SiteBlocked as blocked:
                    print(f"  STOPPED: {source_name} blocked automated access ({blocked}).")
                    print("  We do not try to get around this. Use the site's e-mail alerts instead:")
                    print(f"  {source.email_alert_help}")

    print(f"\nResults are in {settings.database}. Run 'python report.py' to see them.")


if __name__ == "__main__":
    main()
