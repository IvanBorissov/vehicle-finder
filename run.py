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
    """Read result pages for one profile on one site and save the listings.

    How paging works (results are sorted newest first):
      * Always start at page 1, because that is where new ads appear.
      * Each listing counts once per run (promoted ads repeat on many pages).
      * The budget is max_listings_per_run NEW listings. Ones we already
        have are free.
      * When a page shows listings we already have, the new ones are done.
        Then we jump to the page where the last run stopped and keep going
        deeper, to work through the older ads a bit more each day.
      * When the results run out, the search is marked "complete". After
        that, a run stops as soon as it reaches listings we already have.
      * Never more than max_pages_per_run pages (safety cap).
    """
    search_url = source.search_url(profile)
    if not search_url:
        return None
    resume_page, complete = storage.get_progress(profile.name, source.name, search_url)
    if complete:
        print("  (this search was read to the end before: checking only for new ads)")
    elif resume_page > 1:
        print(f"  (last run stopped at page {resume_page})")

    counts = {"new": 0, "price changed": 0, "seen before": 0, "rejected": 0}
    seen_this_run = set()   # listing ids already handled in this run
    new_listings = 0        # counts toward the budget
    page_number = 1
    pages_loaded = 0
    jumped = False
    results_ended = False

    while True:
        if pages_loaded >= settings.max_pages_per_run:
            print(f"    reached the safety cap of {settings.max_pages_per_run} pages for this run")
            break

        url = source.page_url(search_url, page_number)
        print(f"  page {page_number}: {url}")
        page = browser.open(url)          # may raise SiteBlocked
        pages_loaded += 1
        listings = [l for l in source.parse_results(page) if l.listing_id not in seen_this_run]
        print(f"    found {len(listings)} listings on this page (not counting repeats)")
        if not listings:
            results_ended = True           # empty page, or only repeats: no more results
            print("    no more results: this search has been read to the end")
            break

        page_had_known = False
        budget_full = False
        for listing in listings:
            seen_this_run.add(listing.listing_id)
            reason = check_listing(listing, profile, settings)
            result = storage.save(profile.name, listing, reason)
            if result == "new":
                new_listings += 1
            else:
                page_had_known = True
            if reason:
                counts["rejected"] += 1
            else:
                counts[result] += 1
                if result == "new":
                    price = f"€{listing.price_eur:,}" if listing.price_eur else "no price"
                    print(f"    NEW  {listing.title} | {price} | {listing.mileage_km or '?'} km | {listing.location or ''}")
            if new_listings >= settings.max_listings_per_run:
                budget_full = True
                break

        if budget_full:
            print(f"    reached the budget of {settings.max_listings_per_run} new listings for this run")
            break                          # next run carries on from this page

        if page_had_known:
            if complete:
                print("    reached listings we already have: nothing newer, stopping")
                break
            if not jumped and resume_page > page_number + 1:
                print(f"    reached listings we already have: jumping to page {resume_page}, where the last run stopped")
                page_number = resume_page
                jumped = True
                continue
        page_number += 1

    # Remember where to carry on next time. Never move the saved place
    # backwards (a run that stopped early near the top must not undo it).
    if results_ended:
        storage.set_progress(profile.name, source.name, search_url, page_number, True)
    elif not complete:
        storage.set_progress(profile.name, source.name, search_url, max(resume_page, page_number), False)
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
                url = SOURCES[source_name]().search_url(profile)
                if url:
                    print("  ", url)
                    print(f"   (then more pages, at most {settings.max_pages_per_run} per run)")
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
                    if counts is not None:
                        print(f"  done: {counts}")
                except SiteBlocked as blocked:
                    print(f"  STOPPED: {source_name} blocked automated access ({blocked}).")
                    print("  We do not try to get around this. Use the site's e-mail alerts instead:")
                    print(f"  {source.email_alert_help}")

    print(f"\nResults are in {settings.database}. Run 'python report.py' to see them.")


if __name__ == "__main__":
    main()
