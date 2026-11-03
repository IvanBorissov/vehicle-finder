"""Saves listings in a local SQLite database (one file, data/vehicles.db).

Each row is one listing for one profile. If we see the same listing again
on a later run, we update it (last_seen, price) instead of adding it twice.
That is how we "remember" listings we already found.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    profile             TEXT NOT NULL,
    source              TEXT NOT NULL,
    listing_id          TEXT NOT NULL,
    title               TEXT,
    price_eur           INTEGER,
    mileage_km          INTEGER,
    first_registration  TEXT,
    fuel                TEXT,
    location            TEXT,
    country             TEXT,
    seller              TEXT,
    url                 TEXT,
    rejected_reason     TEXT,      -- NULL means the listing passed our checks
    first_seen          TEXT,
    last_seen           TEXT,
    times_seen          INTEGER DEFAULT 1,
    previous_price_eur  INTEGER,   -- set when the price changes
    raw_json            TEXT,
    PRIMARY KEY (profile, source, listing_id)
);

-- Where each search stopped last time, so the next run can go deeper.
CREATE TABLE IF NOT EXISTS search_progress (
    profile      TEXT NOT NULL,
    source       TEXT NOT NULL,
    search_url   TEXT,              -- page-1 URL; if it changes, we start over
    resume_page  INTEGER DEFAULT 1, -- the next page to read when going deeper
    complete     INTEGER DEFAULT 0, -- 1 = we have read every result page once
    updated      TEXT,
    PRIMARY KEY (profile, source)
);
"""


class Storage:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def save(self, profile_name, listing, rejected_reason) -> str:
        """Insert or update. Returns 'new', 'price changed' or 'seen before'."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        old = self.db.execute(
            "SELECT price_eur FROM listings WHERE profile=? AND source=? AND listing_id=?",
            (profile_name, listing.source, listing.listing_id),
        ).fetchone()

        if old is None:
            self.db.execute(
                """INSERT INTO listings (profile, source, listing_id, title, price_eur, mileage_km,
                       first_registration, fuel, location, country, seller, url, rejected_reason,
                       first_seen, last_seen, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (profile_name, listing.source, listing.listing_id, listing.title, listing.price_eur,
                 listing.mileage_km, listing.first_registration, listing.fuel, listing.location,
                 listing.country, listing.seller, listing.url, rejected_reason, now, now,
                 json.dumps(listing.raw, ensure_ascii=False)),
            )
            result = "new"
        else:
            price_changed = listing.price_eur is not None and listing.price_eur != old["price_eur"]
            self.db.execute(
                """UPDATE listings SET last_seen=?, times_seen=times_seen+1, price_eur=?,
                       previous_price_eur=CASE WHEN ? THEN price_eur ELSE previous_price_eur END,
                       rejected_reason=?
                   WHERE profile=? AND source=? AND listing_id=?""",
                (now, listing.price_eur if listing.price_eur is not None else old["price_eur"],
                 price_changed, rejected_reason, profile_name, listing.source, listing.listing_id),
            )
            result = "price changed" if price_changed else "seen before"
        self.db.commit()
        return result

    def accepted(self, profile_name=None):
        """All listings that passed the checks, newest first."""
        sql = "SELECT * FROM listings WHERE rejected_reason IS NULL"
        args = ()
        if profile_name:
            sql += " AND profile=?"
            args = (profile_name,)
        return self.db.execute(sql + " ORDER BY first_seen DESC, price_eur", args).fetchall()

    def rejected(self, profile_name=None):
        sql = "SELECT * FROM listings WHERE rejected_reason IS NOT NULL"
        args = ()
        if profile_name:
            sql += " AND profile=?"
            args = (profile_name,)
        return self.db.execute(sql + " ORDER BY first_seen DESC", args).fetchall()

    def get_progress(self, profile_name, source_name, search_url):
        """Return (resume_page, complete) for this search.

        A new search, or one whose URL changed (different criteria),
        starts again from page 1 and is not complete.
        """
        row = self.db.execute(
            "SELECT search_url, resume_page, complete FROM search_progress WHERE profile=? AND source=?",
            (profile_name, source_name),
        ).fetchone()
        if row is None or row["search_url"] != search_url:
            return 1, False
        return row["resume_page"], bool(row["complete"])

    def set_progress(self, profile_name, source_name, search_url, resume_page, complete):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.db.execute(
            """INSERT INTO search_progress (profile, source, search_url, resume_page, complete, updated)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT (profile, source) DO UPDATE SET
                   search_url=excluded.search_url, resume_page=excluded.resume_page,
                   complete=excluded.complete, updated=excluded.updated""",
            (profile_name, source_name, search_url, resume_page, int(complete), now),
        )
        self.db.commit()
