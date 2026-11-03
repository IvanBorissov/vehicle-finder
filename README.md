# vehicle-finder

Finds used vehicles on European listing sites that match your search
profiles, and saves them in a local database. Later stages add AI checks and
a Telegram channel post.

**Stage 1 (now):** search AutoScout24 and mobile.de, save results in
`data/vehicles.db`, look at them with `report.py`. No AI calls yet.

## How it is built

```
config/profiles.toml     your searches (one [[profiles]] block per search) + shared rules
run.py                   runs every enabled profile on every site it lists
report.py                prints what was found, writes data/report.csv for Excel
finder/
  profiles.py            reads profiles.toml
  browser.py             opens pages at human pace; stops if a site shows a bot check
  sources/autoscout24.py one file per website: builds the search URL, reads the results
  sources/mobile_de.py
  filters.py             double-checks price, model, fuel and "drivable" keywords
  storage.py             SQLite: remembers listings, notices price changes
tests/                   offline tests on small hand-made pages
```

Ground rules the code follows: a random 6–14 second pause between pages, at
most 8 pages and 60 new listings per search per run, listings seen before are
updated instead of added again, and if a site shows a captcha or "access
denied" the program stops for that site and tells you to use the site's
e-mail alerts instead. It never tries to get around bot protection.

Paging: each run starts at page 1 (newest ads). When it reaches ads it already
has, it jumps to the page where the last run stopped and goes deeper, so the
older ads get worked through over several days. Once a search has been read
to the end, runs only check the first pages for new ads.

## Run it (first time)

You need Python 3.11 or newer ([python.org](https://www.python.org/downloads/);
on Windows tick "Add python.exe to PATH" during install).

1. In GitHub Desktop, switch to this branch (or `main` once merged) and click
   **Repository → Open in Command Prompt** (Mac: **Open in Terminal**).
2. Create a private Python environment and install the two dependencies:

   Windows:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   playwright install chromium
   ```
   Mac / Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Check everything works offline: `python -m unittest` (should say `OK`).
4. See which URLs it would open, without loading anything: `python run.py --dry-run`
5. Run a real search: `python run.py`
6. See the results: `python report.py` and `python report.py --rejected`
   (also saved as `data/report.csv` and `data/rejected.csv`).

Next time you only need the `activate` line, then steps 5 and 6.

Tip: set `show_browser = true` in `config/profiles.toml` to watch the browser.

## mobile.de

mobile.de uses its own codes for makes and models, so it needs a search URL
from you: open suchen.mobile.de, set make, model, fuel, max price, radius and
the "not damaged" filter, press search, copy the address bar and paste it into
`config/profiles.toml` under `[profiles.search_urls]` → `mobile_de`.
mobile.de is known to block automated browsers. If it does, the program will
say so and stop; in that case use mobile.de's saved-search e-mail alerts.

## Add another search

Copy a `[[profiles]]` block in `config/profiles.toml`, give it a new `name`,
change the criteria, and set `enabled = true`. Every profile is stored
separately in the database.

## If a site returns 0 listings

Sites change their pages. The program saves the page it could not read in
`debug/` (ignored by git). Send that file over and the reader can be fixed.
