from datetime import datetime
from seasonal_modes import automatic_mode_id
from country_resolver import resolve_country

def check(label, condition):
    if not condition:
        raise AssertionError(label)
    print(label + ": OK")

# Korea-specific events
mode, tz, info = automatic_mode_id("Asia/Seoul", "KR")
check("country resolver KR", info["country"] == "KR")
check("timezone KR", tz == "Asia/Seoul")

# Locale mismatch: timezone should win
info = resolve_country("America/New_York", "KR")
check("timezone beats locale", info["country"] == "US")
check("mismatch flagged", info["mismatch"] is True)

# Unknown timezone mapping can use locale fallback
info = resolve_country("Etc/UTC", "GB")
check("locale fallback", info["country"] == "GB")

print("Time/event self-test complete")
