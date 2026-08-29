from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

from accurate_time import now_in_timezone, validate_timezone, seconds_until_next_local_midnight
from country_resolver import resolve_country



# Country-specific events use that country's local date.
# International events use the viewer/user timezone supplied by the browser.
COUNTRY_TIMEZONES = {
    "KR": "Asia/Seoul",
    "JP": "Asia/Tokyo",
    "US": "America/New_York",
    "GB": "Europe/London",
    "FR": "Europe/Paris",
    "DE": "Europe/Berlin",
    "AU": "Australia/Sydney",
    "CA": "America/Toronto",
    "CN": "Asia/Shanghai",
    "IN": "Asia/Kolkata",
    "BR": "America/Sao_Paulo",
}



@dataclass
class SeasonalMode:
    id: str
    name: str
    active: bool
    automatic: bool
    banner: str
    emoji: str
    accent: str
    celebration_title: str
    celebration_message: str
    decoration: str
    scope: str
    country: str | None
    timezone: str
    country_source: str
    country_mismatch: bool
    seconds_until_recheck: int
    system_instruction: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MODES = {
    "none": {
        "name": "기본 모드",
        "scope": "none",
        "country": None,
        "banner": "",
        "emoji": "",
        "accent": "default",
        "celebration_title": "",
        "celebration_message": "",
        "decoration": "none",
        "instruction": "",
    },

    "new_year": {
        "name": "새해 모드",
        "scope": "international",
        "country": None,
        "banner": "새해가 시작되었습니다. PICK이 산뜻한 새해 분위기로 함께합니다 🎉",
        "emoji": "🎉",
        "accent": "newyear",
        "celebration_title": "새해 복 많이 받으세요",
        "celebration_message": "새로운 한 해의 시작을 PICK과 함께합니다.",
        "decoration": "confetti",
        "instruction": """[New Year mode]
- Use a hopeful, fresh tone when appropriate.
- Do not force celebratory language into serious or technical requests.
- Accuracy and task completion remain the priority.
""",
    },

    "samil": {
        "name": "삼일절 모드",
        "scope": "country",
        "country": "KR",
        "banner": "삼일절입니다. 차분하고 존중하는 분위기로 답합니다 🇰🇷",
        "emoji": "🇰🇷",
        "accent": "samil",
        "celebration_title": "삼일절",
        "celebration_message": "독립을 위해 힘쓴 분들을 기억하며 차분하게 기념합니다.",
        "decoration": "taegeuk",
        "instruction": """[March 1st mode]
- Keep a respectful and calm tone.
- Do not turn unrelated technical or factual answers into commemorative commentary.
- Preserve accuracy and neutrality.
""",
    },

    "april_fools": {
        "name": "만우절 모드",
        "scope": "international",
        "country": None,
        "banner": "오늘은 만우절입니다. PICK이 조금 더 장난스럽게 말합니다 🎭",
        "emoji": "🎭",
        "accent": "april",
        "celebration_title": "오늘은 만우절",
        "celebration_message": "화면에 작은 장난이 숨어 있을 수 있습니다. 답변의 사실성은 그대로입니다.",
        "decoration": "sparkles",
        "instruction": """[April Fools mode]
- Make the April Fools event clearly noticeable in ordinary low-stakes conversation with playful wording, a tiny harmless joke, or a fitting emoji.
- A joke must be obviously playful or immediately followed by a clear correction such as '농담입니다'.
- Never fabricate facts, warnings, purchases, emergencies, prices, weather, navigation, postal codes, news, code results, translations, or user data.
- Serious, safety-related, factual, technical, legal, medical, weather, navigation, postal, news, coding, and translation requests must remain precise.
- Factual accuracy always wins over the event theme.
""",
    },

    "childrens_day": {
        "name": "어린이날 모드",
        "scope": "country",
        "country": "KR",
        "banner": "어린이날입니다. 밝고 친근한 분위기로 답합니다 🌈",
        "emoji": "🌈",
        "accent": "children",
        "celebration_title": "즐거운 어린이날",
        "celebration_message": "호기심과 상상력이 빛나는 하루를 기념합니다.",
        "decoration": "bubbles",
        "instruction": """[Children's Day mode]
- Use a warm, clear, friendly tone.
- Keep explanations easy to follow when appropriate.
- Never make technical answers childish or less precise.
""",
    },

    "memorial_day": {
        "name": "현충일 모드",
        "scope": "country",
        "country": "KR",
        "banner": "현충일입니다. 차분하고 절제된 분위기로 답합니다 🕊️",
        "emoji": "🕊️",
        "accent": "memorial",
        "celebration_title": "현충일",
        "celebration_message": "희생과 헌신을 기억하며 차분하고 절제된 화면을 사용합니다.",
        "decoration": "memorial",
        "instruction": """[Memorial Day mode]
- Use a restrained and respectful tone.
- Do not add celebratory decorations to serious content.
- Accuracy remains the priority.
""",
    },

    "liberation_day": {
        "name": "광복절 모드",
        "scope": "country",
        "country": "KR",
        "banner": "광복절입니다. 차분하고 또렷한 한국어 분위기로 답합니다 🇰🇷",
        "emoji": "🇰🇷",
        "accent": "liberation",
        "celebration_title": "광복절",
        "celebration_message": "광복의 의미를 기억하며 특별한 태극 테마를 적용합니다.",
        "decoration": "taegeuk",
        "instruction": """[Liberation Day mode]
- Use clear and respectful Korean when the user speaks Korean.
- Do not inject political advocacy.
- Preserve factual neutrality and technical accuracy.
""",
    },

    "hangul_day": {
        "name": "한글날 모드",
        "scope": "country",
        "country": "KR",
        "banner": "한글날입니다. 아름답고 또렷한 한국어로 답합니다 ✨",
        "emoji": "✨",
        "accent": "hangul",
        "celebration_title": "한글날",
        "celebration_message": "한글의 아름다움과 가치를 기념합니다. 오늘의 PICK은 한국어 표현도 조금 더 특별합니다.",
        "decoration": "hangul",
        "instruction": """[Hangul Day mode]
- When the user speaks Korean, prefer clear and natural Korean.
- Preserve code, filenames, URLs, APIs, library names, and product names exactly.
- Do not force Korean if the user explicitly requests another language.
- Accuracy is more important than decorative wording.
""",
    },

    "halloween": {
        "name": "할로윈 모드",
        "scope": "international",
        "country": None,
        "banner": "할로윈 모드가 켜졌습니다. 살짝 신비로운 분위기를 더합니다 🎃",
        "emoji": "🎃",
        "accent": "halloween",
        "celebration_title": "Happy Halloween",
        "celebration_message": "PICK에 살짝 신비로운 밤의 분위기가 찾아왔습니다.",
        "decoration": "pumpkins",
        "instruction": """[Halloween mode]
- Light spooky or playful wording is allowed.
- Never distort facts, warnings, code, safety, prices, news, or user data.
- Keep serious requests serious.
""",
    },

    "christmas": {
        "name": "크리스마스 모드",
        "scope": "international",
        "country": None,
        "banner": "크리스마스입니다. 따뜻하고 포근한 분위기로 답합니다 🎄",
        "emoji": "🎄",
        "accent": "christmas",
        "celebration_title": "Merry Christmas",
        "celebration_message": "따뜻한 겨울 분위기와 눈 내리는 PICK을 만나보세요.",
        "decoration": "snow",
        "instruction": """[Christmas mode]
- Use a warm seasonal tone when appropriate.
- Do not force religious or celebratory framing.
- Technical and factual answers must remain precise.
""",
    },

    "year_end": {
        "name": "연말 모드",
        "scope": "international",
        "country": None,
        "banner": "한 해의 마지막 날입니다. 차분하게 마무리하는 분위기로 답합니다 🌙",
        "emoji": "🌙",
        "accent": "yearend",
        "celebration_title": "올해의 마지막 날",
        "celebration_message": "한 해를 돌아보고 새로운 시작을 준비하는 차분한 밤입니다.",
        "decoration": "stars",
        "instruction": """[Year-end mode]
- Use a calm, reflective tone when appropriate.
- Do not add unnecessary sentiment to technical or urgent requests.
""",
    },
}


def _now_in(timezone_name: str | None):
    # The browser supplies only an IANA timezone name.
    # The actual clock comes from the server's NTP-adjusted UTC time.
    return now_in_timezone(timezone_name, "Asia/Seoul")


def _event_for_date(month: int, day: int, *, country: str | None, international_only=False):
    # International/common events are evaluated in the user's own local timezone.
    international = {
        (1, 1): "new_year",
        (4, 1): "april_fools",
        (10, 31): "halloween",
        (12, 25): "christmas",
        (12, 31): "year_end",
    }
    if (month, day) in international:
        return international[(month, day)]

    if international_only:
        return "none"

    # South-Korea-only commemorations are evaluated strictly in Asia/Seoul.
    if country == "KR":
        korea = {
            (3, 1): "samil",
            (5, 5): "childrens_day",
            (6, 6): "memorial_day",
            (8, 15): "liberation_day",
            (10, 9): "hangul_day",
        }
        return korea.get((month, day), "none")

    return "none"


def automatic_mode_id(user_timezone: str | None = None, country: str | None = None):
    tz_name = validate_timezone(user_timezone, "Asia/Seoul")
    country_info = resolve_country(tz_name, country)
    resolved_country = country_info["country"]

    # 1) Country-only event: its own country's timezone controls the date.
    if resolved_country == "KR":
        kr_now = _now_in("Asia/Seoul")
        kr_mode = _event_for_date(kr_now.month, kr_now.day, country="KR")
        if kr_mode != "none" and MODES[kr_mode].get("scope") == "country":
            return kr_mode, "Asia/Seoul", country_info

    # 2) International event: each user sees it when that date arrives locally.
    local_now = _now_in(tz_name)
    mode = _event_for_date(
        local_now.month, local_now.day,
        country=resolved_country,
        international_only=True
    )
    return mode, tz_name, country_info


def resolve_mode(
    user_id: int | None = None,
    user_timezone: str | None = None,
    country: str | None = None,
    override: str | None = None,
) -> SeasonalMode:
    automatic = True
    override_id = str(override or "auto").strip()
    if override_id != "auto" and override_id in MODES:
        timezone_name = validate_timezone(user_timezone, "Asia/Seoul")
        country_info = resolve_country(timezone_name, country)
        mode_id = override_id
        automatic = False
    else:
        mode_id, timezone_name, country_info = automatic_mode_id(user_timezone, country)
    data = MODES[mode_id]

    active_instruction = data["instruction"]
    if mode_id != "none":
        active_instruction += f"""
[Active PICK event: {data['name']}]
- This event mode is active now. In ordinary low-stakes conversation, make the event feel visibly active with one short themed phrase, emoji, or stylistic touch when appropriate.
- Do not force the event theme into serious, urgent, factual, coding, translation, postal, navigation, weather, or news answers.
- Never change facts or user-requested output just to fit the event.
"""

    return SeasonalMode(
        id=mode_id,
        name=data["name"],
        active=mode_id != "none",
        automatic=automatic,
        banner=data["banner"],
        emoji=data["emoji"],
        accent=data["accent"],
        celebration_title=data["celebration_title"],
        celebration_message=data["celebration_message"],
        decoration=data["decoration"],
        scope=data.get("scope", "none"),
        country=data.get("country"),
        timezone=timezone_name,
        country_source=country_info.get("source", "unknown"),
        country_mismatch=bool(country_info.get("mismatch")),
        seconds_until_recheck=min(
            300,
            max(30, seconds_until_next_local_midnight(timezone_name))
        ),
        system_instruction=active_instruction,
    )


def list_modes():
    # Read-only informational list.
    return {
        key: value["name"]
        for key, value in MODES.items()
    }
