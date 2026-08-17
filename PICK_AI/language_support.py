from __future__ import annotations

import re

SUPPORTED_LANGUAGES = {
    "auto": "자동 감지",
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "ru": "Русский",
    "ar": "العربية",
    "hi": "हिन्दी",
    "id": "Bahasa Indonesia",
    "vi": "Tiếng Việt",
    "th": "ไทย",
    "tr": "Türkçe",
    "pl": "Polski",
    "nl": "Nederlands",
    "sv": "Svenska",
    "uk": "Українська",
}

SCRIPT_PATTERNS = [
    ("ko", re.compile(r"[가-힣]")),
    ("ja", re.compile(r"[\u3040-\u30ff]")),
    ("zh-CN", re.compile(r"[\u4e00-\u9fff]")),
    ("ru", re.compile(r"[\u0400-\u04ff]")),
    ("ar", re.compile(r"[\u0600-\u06ff]")),
    ("hi", re.compile(r"[\u0900-\u097f]")),
    ("th", re.compile(r"[\u0e00-\u0e7f]")),
]


def detect_language(text: str) -> str:
    value = str(text or "")
    for code, pattern in SCRIPT_PATTERNS:
        if pattern.search(value):
            return code
    # Latin-script requests default to English unless user selected a language.
    return "en"


def language_instruction(selected: str, user_text: str) -> str:
    code = selected if selected and selected != "auto" else detect_language(user_text)
    display = SUPPORTED_LANGUAGES.get(code, code)
    return (
        f"Answer in {display}. "
        "Preserve code, filenames, URLs, API names, and technical identifiers exactly. "
        "If the user explicitly requests another language in the message, follow that request instead."
    )
