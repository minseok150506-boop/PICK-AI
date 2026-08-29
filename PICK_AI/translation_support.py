from __future__ import annotations

import re

LANGUAGE_ALIASES = {
    "한국어": "Korean", "한글": "Korean", "영어": "English", "영문": "English",
    "일본어": "Japanese", "일어": "Japanese", "중국어": "Chinese", "중문": "Chinese",
    "간체": "Simplified Chinese", "번체": "Traditional Chinese", "대만어": "Traditional Chinese",
    "프랑스어": "French", "불어": "French", "독일어": "German", "스페인어": "Spanish",
    "이탈리아어": "Italian", "포르투갈어": "Portuguese", "러시아어": "Russian",
    "아랍어": "Arabic", "힌디어": "Hindi", "베트남어": "Vietnamese", "태국어": "Thai",
    "인도네시아어": "Indonesian", "터키어": "Turkish", "폴란드어": "Polish",
    "네덜란드어": "Dutch", "스웨덴어": "Swedish", "우크라이나어": "Ukrainian",
}

TRANSLATION_WORDS = ("번역", "translate", "translation", "통역")


def is_translation_request(text: str) -> bool:
    t = str(text or "").lower()
    return any(word in t for word in TRANSLATION_WORDS)


def detect_target_language(text: str) -> str | None:
    value = str(text or "")
    for alias, language in LANGUAGE_ALIASES.items():
        if re.search(re.escape(alias) + r"\s*(?:로|으로|번역)", value):
            return language
    lower = value.lower()
    english_aliases = {
        "english": "English", "japanese": "Japanese", "korean": "Korean",
        "chinese": "Chinese", "french": "French", "german": "German",
        "spanish": "Spanish", "italian": "Italian", "portuguese": "Portuguese",
        "russian": "Russian",
    }
    for alias, language in english_aliases.items():
        if alias in lower:
            return language
    return None


def translation_instruction(text: str) -> str:
    if not is_translation_request(text):
        return ""
    target = detect_target_language(text)
    target_rule = (
        f"Target language explicitly detected: {target}."
        if target
        else "If the target language is clear from context, use it. If it is genuinely missing, ask one short clarification."
    )
    return f"""[Translation mode]
{target_rule}
- Translate the user's requested source faithfully and completely.
- Preserve meaning, tone, names, numbers, dates, URLs, filenames, code, placeholders, variables, tags, and product names unless localization specifically requires a change.
- Do not summarize, omit, or add information unless the user asks.
- For UI/game localization, keep terminology consistent throughout the text.
- If the user requests source + translation, put each translated segment immediately below its source segment.
- Do not translate code blocks unless the user explicitly asks to translate comments or strings.
"""
