# CLAUDE.md

Notes for Claude Code working in this repo. Ivan owns the project. He is
learning to code, so keep the code readable, explain each change in simple
words, and prefer small, clear steps over clever ones.

## What this project is

A modular "closed loop of agents" that finds used cars and vans on European
sites and auctions, checks each other's work, and posts a shortlist to a
private Telegram channel (Ivan and one friend). It is a learning project.

Pipeline (planned): criteria -> search -> validator -> scoring (+ vision on
photos) -> critic -> Telegram post.

Stages:
1. One search source into SQLite (done: AutoScout24 + mobile.de, needs live testing)
2. The agent loop (validator, scoring, critic)
3. Vision on listing photos
4. Telegram delivery + daily schedule

## Layout

- `config/profiles.toml`: search profiles (several allowed) plus shared rules (pace, limits, not-drivable words)
- `finder/profiles.py`: loads the config
- `finder/browser.py`: Playwright at human pace; raises `SiteBlocked` on bot checks
- `finder/sources/`: one file per website, registered in `finder/sources/__init__.py`
- `finder/filters.py`: plain-code checks (price, model, fuel, drivable keywords)
- `finder/storage.py`: SQLite in `data/vehicles.db`; remembers listings, tracks price changes
- `run.py` runs the searches, `report.py` shows the results and writes CSVs to `data/`
- Later: `finder/agents/` (AI judging) and `finder/delivery/` (Telegram)

Keep these modules separate. A new site is a new file in `finder/sources/`.

## Commands

```
python -m venv .venv            # once
.venv\Scripts\activate          # Windows (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
playwright install chromium
python -m unittest              # offline tests, should say OK
python run.py --dry-run         # print search URLs only
python run.py                   # real search
python report.py                # results (add --rejected to see skipped ones)
```

Run `python -m unittest` before every commit.

## Rules (agreed with Ivan, do not break)

- **Be polite to sites.** Keep the random pauses and the page and listing limits in `profiles.toml`. Never send requests in parallel to one site.
- **Never get around bot protection.** No stealth plugins, no captcha solving, no rotating proxies, no faked fingerprints. If a site blocks us, stop and tell Ivan. The fallback is that site's saved-search e-mail alerts.
- **Never contact sellers** and never send messages anywhere except the private Telegram channel.
- **Code extracts, AI only judges.** Parse pages with code. Use Claude API calls only for judging (scoring, photos, critic), from Stage 2 on.
- **Budget.** About EUR 10 prepaid for the API. Use Haiku for the first pass and Sonnet only for finalists, shrink photos before sending, use the Batch API where possible, and respect a daily spend cap.
- **Secrets** (API key, Telegram token) live only in `.env`, which git ignores. Never print, log or commit them. `.env.example` shows the variable names.
- Never commit `data/`, `debug/` or `*.db`.

## Working with Ivan

- `PROGRESS.md` is the shared log between Claude Desktop and Claude Code. Read it at the start of a session. At the end, add a short dated entry at the top of "Log" and update the status, open questions and next steps.

- Ivan uses GitHub Desktop for git. Tell him what to click or run, step by step.
- Explain what you changed and why in a few plain sentences.
- Ask before big changes (new dependencies, new folders, a changed database schema).
- When a site's page changes and parsing breaks, the page is saved in `debug/`. Read it there and fix the matching file in `finder/sources/`.
