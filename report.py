"""Show what is in the database and write a CSV you can open in Excel.

Usage:
    python report.py                 # listings that passed the checks
    python report.py --rejected      # listings we skipped, and why
    python report.py --profile caddy-diesel-frankfurt
"""

import argparse
import csv
from pathlib import Path

from finder.profiles import load_config
from finder.storage import Storage

COLUMNS = ["profile", "source", "title", "price_eur", "mileage_km", "first_registration",
           "fuel", "location", "seller", "first_seen", "times_seen", "previous_price_eur",
           "rejected_reason", "url"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/profiles.toml")
    parser.add_argument("--profile")
    parser.add_argument("--rejected", action="store_true")
    args = parser.parse_args()

    settings, _ = load_config(args.config)
    storage = Storage(settings.database)
    rows = storage.rejected(args.profile) if args.rejected else storage.accepted(args.profile)

    for row in rows:
        price = f"€{row['price_eur']:,}" if row["price_eur"] else "no price"
        line = f"{row['title'][:45]:45} {price:>9} {str(row['mileage_km'] or '?'):>7} km  {row['first_registration'] or '':8} {row['location'] or ''}"
        if args.rejected:
            line += f"  <- {row['rejected_reason']}"
        print(line)
        print(f"    {row['url']}")

    out = Path("data") / ("rejected.csv" if args.rejected else "report.csv")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")   # ';' opens correctly in German/EU Excel
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([row[c] for c in COLUMNS])
    print(f"\n{len(rows)} listings. Also saved to {out}")


if __name__ == "__main__":
    main()
