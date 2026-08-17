from __future__ import annotations

TIMEZONE_COUNTRY = {
    "Asia/Seoul": "KR",
    "Asia/Tokyo": "JP",
    "Asia/Shanghai": "CN",
    "Asia/Hong_Kong": "HK",
    "Asia/Taipei": "TW",
    "Asia/Singapore": "SG",
    "Asia/Kolkata": "IN",
    "Europe/London": "GB",
    "Europe/Paris": "FR",
    "Europe/Berlin": "DE",
    "Europe/Rome": "IT",
    "Europe/Madrid": "ES",
    "Europe/Warsaw": "PL",
    "Europe/Amsterdam": "NL",
    "Europe/Stockholm": "SE",
    "Europe/Kyiv": "UA",
    "America/New_York": "US",
    "America/Chicago": "US",
    "America/Denver": "US",
    "America/Los_Angeles": "US",
    "America/Toronto": "CA",
    "America/Vancouver": "CA",
    "America/Sao_Paulo": "BR",
    "Australia/Sydney": "AU",
    "Australia/Melbourne": "AU",
    "Pacific/Auckland": "NZ",
}

REGION_PREFIXES = [
    ("America/", None),
    ("Europe/", None),
    ("Asia/", None),
    ("Australia/", "AU"),
]


def resolve_country(timezone_name: str | None, locale_country: str | None = None) -> dict:
    tz = str(timezone_name or "")
    locale = str(locale_country or "").upper().strip() or None
    tz_country = TIMEZONE_COUNTRY.get(tz)

    # Exact timezone mapping is stronger than browser locale.
    if tz_country:
        return {
            "country": tz_country,
            "source": "timezone",
            "locale_country": locale,
            "timezone_country": tz_country,
            "mismatch": bool(locale and locale != tz_country),
        }

    # If timezone cannot identify a country, use locale as a weak fallback.
    return {
        "country": locale,
        "source": "locale" if locale else "unknown",
        "locale_country": locale,
        "timezone_country": None,
        "mismatch": False,
    }
