"""Reads config/profiles.toml and turns it into Python objects.

A *profile* is one saved search (make, model, budget, area, ...).
*Settings* are the rules shared by every search (pace, limits, database).
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    database: str = "data/vehicles.db"
    pause_seconds: tuple[float, float] = (6, 14)
    max_pages_per_search: int = 3
    max_listings_per_run: int = 60
    show_browser: bool = False
    not_drivable_words: list[str] = field(default_factory=list)


@dataclass
class Profile:
    name: str
    make: str
    model: str
    max_price_eur: int
    fuel: str = "diesel"
    center_zip: str = "60311"
    center_lat: float = 50.1109
    center_lon: float = 8.6821
    radius_km: int = 350
    countries: list[str] = field(default_factory=lambda: ["DE"])
    must_be_drivable: bool = True
    sources: list[str] = field(default_factory=lambda: ["autoscout24"])
    # Optional exact URLs per site, pasted from the browser.
    search_urls: dict[str, str] = field(default_factory=dict)
    enabled: bool = True


def load_config(path: str | Path = "config/profiles.toml") -> tuple[Settings, list[Profile]]:
    """Return (settings, list of enabled profiles) from the TOML file."""
    with open(path, "rb") as f:
        data = tomllib.load(f)

    raw_settings = data.get("settings", {})
    if "pause_seconds" in raw_settings:
        raw_settings["pause_seconds"] = tuple(raw_settings["pause_seconds"])
    settings = Settings(**raw_settings)

    profiles = []
    names = set()
    for raw in data.get("profiles", []):
        profile = Profile(**raw)
        if profile.name in names:
            raise ValueError(f"Two profiles are called '{profile.name}'. Names must be unique.")
        names.add(profile.name)
        if profile.enabled:
            profiles.append(profile)
    return settings, profiles
