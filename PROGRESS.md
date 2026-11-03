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
| 1. Search into SQLite | AutoScout24 **works live** (tested 2026-11-03). mobile.de waiting for a search URL from Ivan. |
| 2. Agent loop (validator, scoring, critic) | Not started |
| 3. Vision on photos | Not started |
| 4. Telegram + daily schedule | Not started |

Working branch: `feature/testing-search`

## Open questions

- Raise `max_listings_per_run` above 60 for the first big run? (The first run hit the limit on page 3.)

## Next steps

1. Ivan: set up the Caddy search on suchen.mobile.de, copy the URL, paste it into `config/profiles.toml` (or send it to Claude Code), then test it live.
2. Small fixes in the AutoScout24 reader (see "Known issues").
3. Plan Stage 2 together before writing code (new `finder/agents/` folder and the `anthropic` library need Ivan's OK).

## Known issues

- Promoted ads appear twice in one run. The database stores them once, but they count twice toward the 60-listing limit.
- Some titles repeat the model ("Volkswagen Caddy Caddy 1.6 TDI") because the seller typed it again. Cosmetic.

## Log

### 2026-11-03: Claude Code, first live test

- Set up the Mac: `.venv`, Playwright 1.64.1 and Chromium. `python -m unittest`: 6 tests OK. `python run.py --dry-run`: URLs look right.
- Live run `python run.py --source autoscout24` (profile `caddy-diesel-frankfurt`):
  - No bot check, no block. 3 pages × 20 listings, stopped at the 60 limit.
  - 58 different listings saved: **57 passed**, 1 rejected (ad said "export").
  - Every listing had price, mileage, first registration, fuel, location and seller filled in. Nothing went to `debug/`.
  - Prices €2,850–€10,000. Countries DE, NL, BE, FR. Panel vans ("Kasten", "Bestel") are included, so `atype=C` does not miss them.
- No code changes.
