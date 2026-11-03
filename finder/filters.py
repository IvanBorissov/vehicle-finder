"""Double-checks every listing against the profile, in plain code.

The sites already filter for us, but their filters are not perfect (wrong
category, sponsored ads, damaged cars without the damage tick box). So we
check again and write down WHY a listing was rejected.
"""

FUEL_NAMES = {
    "diesel": ["diesel"],
    "petrol": ["benzin", "petrol", "gasoline", "super"],
    "electric": ["elektro", "electric"],
    "hybrid": ["hybrid"],
    "lpg": ["lpg", "autogas"],
}


def check_listing(listing, profile, settings) -> str | None:
    """Return None if the listing is OK, or a short reason why it is not."""
    title = (listing.title or "").lower()

    if listing.price_eur is not None and listing.price_eur > profile.max_price_eur:
        return f"price {listing.price_eur} over budget {profile.max_price_eur}"

    if profile.model.lower() not in title:
        return f"title does not mention '{profile.model}'"

    if listing.fuel and profile.fuel in FUEL_NAMES:
        fuel = listing.fuel.lower()
        if not any(name in fuel for name in FUEL_NAMES[profile.fuel]):
            return f"fuel is {listing.fuel}"

    if profile.must_be_drivable:
        # Search title, plus card text for sites that give us one.
        text = title + " " + str(listing.raw.get("card_text", "")).lower()
        for word in settings.not_drivable_words:
            if word.lower() in text:
                return f"not drivable? mentions '{word}'"

    return None
