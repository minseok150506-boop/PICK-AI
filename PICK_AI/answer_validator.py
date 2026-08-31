from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class ValidationResult:
    ok: bool
    warnings: list[str]
    cleaned: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_answer(answer: str, *, web_used=False, coding=False) -> ValidationResult:
    text = str(answer or "").strip()
    warnings = []

    # Never expose internal reasoning labels in user-facing output.
    banned_markers = [
        "Chain of Thought",
        "Internal reasoning",
        "숨겨진 추론",
        "내부 추론 과정",
        "Brain:",
        "Thinking:",
    ]
    for marker in banned_markers:
        if marker.lower() in text.lower():
            warnings.append(f"internal-marker:{marker}")
            text = re.sub(re.escape(marker), "", text, flags=re.I)

    if web_used and not re.search(r"(출처|source|http[s]?://)", text, re.I):
        warnings.append("web-answer-without-visible-source")

    if coding and "```" not in text and len(text) > 500:
        warnings.append("coding-answer-without-code-block")

    # Avoid accidental repeated duplicate paragraphs.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    deduped = []
    seen = set()
    for p in paragraphs:
        key = re.sub(r"\s+", " ", p).strip().lower()
        if key in seen:
            warnings.append("duplicate-paragraph")
            continue
        seen.add(key)
        deduped.append(p)
    text = "\n\n".join(deduped)

    return ValidationResult(ok=not warnings, warnings=warnings, cleaned=text)
