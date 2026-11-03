# Progress log

Shared notes between Ivan, Claude Desktop and Claude Code.
**Read this first, and update it at the end of every work session.**

- Put the newest log entry at the top of "Log".
- Keep "Current status", "Open questions" and "Next steps" up to date (edit them, don't just add).
- Summaries only: no secrets, no full listing dumps (those live in `data/`, which git ignores).

## Who does what

| Who | Good at |
|---|---|
| Claude Desktop | Planning, design discussions, writing code in the sandbox |
| Claude Code (on Ivan's Mac) | Running things for real: live site searches, tests, Playwright, reading `debug/` pages, git |
| Ivan | Decisions, GitHub Desktop (commit, push, merge), copying search URLs from the browser |

## Current status

| Stage | State |
|---|---|
| 1. Search into SQLite | AutoScout24 **works live**, with deeper paging (tested 2026-11-03). mobile.de waiting for a search URL from Ivan. |
| 2. Agent loop (validator, scoring, critic) | Not started |
| 3. Vision on photos | Not started |
| 4. Telegram + daily schedule | Not started |

Working branch: `feature/testing-search`

## Open questions

- How does AutoScout24 behave past the last results page (empty page, or a repeat of the last page)? Both count as "results ended", but we haven't seen it live yet. AutoScout24 may also stop at about 20 pages (400 ads), even if there are more.

## Next steps

1. Ivan: set up the Caddy search on suchen.mobile.de, copy the URL, paste it into `config/profiles.toml` (or send it to Claude Code), then test it live.
2. Tidy the doubled model in titles (see "Known issues").
3. Plan Stage 2 together before writing code (new `finder/agents/` folder and the `anthropic` library need Ivan's OK).

## Known issues

- Some titles repeat the model ("Volkswagen Caddy Caddy 1.6 TDI") because the seller typed it again. Cosmetic.
- Changing a profile's criteria changes its search URL, so the saved paging place resets to page 1 (on purpose).

## How paging works (since 2026-11-03)

- Every run starts at page 1 (sorted newest first).
- Each listing counts once per run (promoted ads repeat on many pages).
- Budget = `max_listings_per_run` (60) NEW listings. Ones we already have don't count.
- When a page shows listings we already have, jump to the page where the last run stopped (table `search_progress`, one row per profile and site) and go deeper.
- When the results end (empty page, or only repeats), the search is marked complete. After that, a run stops at the first page with known listings.
- Safety cap: `max_pages_per_run` (8) in `profiles.toml`, with the same pauses.

## Log

### 2026-11-03: Claude Code, deeper paging (task from Claude Desktop)

- Code: `run.py` has the new paging loop. Each source now gives one `search_url()`, and `Source.page_url()` adds the page number (`page` for AutoScout24, `pageNumber` for mobile.de). The new table `search_progress` is in `finder/storage.py`. In `profiles.toml`, `max_pages_per_search = 3` was replaced by `max_pages_per_run = 8`. README updated.
- Tests: new `tests/test_paging.py` (7 tests, fake site, offline): repeats counted once, budget counts only new, jump to the saved page, complete search checks only the top, page cap, saved place never moves back, changed search starts over. `python -m unittest`: 13 tests OK.
- Live run (AutoScout24, Caddy profile): pages 1–3 held the 57 known listings, pages 4–7 gave **60 new**, and it stopped at the budget on page 7. Promoted repeats were skipped (pages showed 18–20 unique). No block, nothing in `debug/`.
- Database now: 118 listings, 117 passed. Saved place: page 7, not complete. The next run checks page 1 for new ads, then jumps to page 7.
- The mobile.de change (`search_url`/`page_url`) has not been tested live yet (still no URL).
- **Decision (Ivan):** stay with SQLite (`data/vehicles.db`) for now. Think again about PostgreSQL only if the program moves to a server (Stage 4). Only `finder/storage.py` touches the database, so a later switch stays small.

### 2026-11-03: Claude Code, first live test

- Set up the Mac: `.venv`, Playwright 1.64.1 and Chromium. `python -m unittest`: 6 tests OK. `python run.py --dry-run`: URLs look right.
- Live run `python run.py --source autoscout24` (profile `caddy-diesel-frankfurt`):
  - No bot check, no block. 3 pages × 20 listings, stopped at the 60 limit.
  - 58 different listings saved: **57 passed**, 1 rejected (ad said "export").
  - Every listing had price, mileage, first registration, fuel, location and seller filled in. Nothing went to `debug/`.
  - Prices €2,850–€10,000. Countries DE, NL, BE, FR. Panel vans ("Kasten", "Bestel") are included, so `atype=C` does not miss them.
- No code changes.
