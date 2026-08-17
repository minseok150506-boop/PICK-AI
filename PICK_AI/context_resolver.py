from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


REFERENCE_TERMS = {
    "이거", "그거", "저거", "이것", "그것", "저것",
    "아까", "전에", "위에", "그 파일", "그 코드", "그 버튼",
    "그걸", "그걸로", "그렇게", "그 방법", "그 모델", "그 주소",
}


@dataclass
class ContextResolution:
    has_reference: bool
    resolved: bool
    referent_summary: str
    source_message_index: int | None
    confidence: float
    context_excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _score_candidate(text: str, user_message: str, distance: int) -> float:
    score = 0.0
    t = text.lower()
    u = user_message.lower()

    technical = re.findall(r"[A-Za-z][A-Za-z0-9_.:+#/-]{2,}|[가-힣]{2,}", u)
    for token in technical:
        if token.lower() in t:
            score += 1.5

    if any(x in t for x in ["오류", "에러", "error", "exception", "파일", "버튼", "모델", "서버", "코드"]):
        score += 0.8

    score += max(0, 1.5 - distance * 0.2)
    return score


def resolve_reference(user_message: str, history: list[dict] | None = None) -> ContextResolution:
    history = history or []
    message = str(user_message or "").strip()
    has_ref = any(term in message for term in REFERENCE_TERMS)

    if not has_ref:
        return ContextResolution(False, False, "", None, 0.0, "")

    candidates = []
    for rev_idx, item in enumerate(reversed(history[-12:])):
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        role = item.get("role", "")
        distance = rev_idx
        score = _score_candidate(content, message, distance)
        if role == "user":
            score += 0.3
        candidates.append((score, len(history[-12:]) - 1 - rev_idx, content))

    if not candidates:
        return ContextResolution(True, False, "", None, 0.0, "")

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, idx, content = candidates[0]
    confidence = min(1.0, best_score / 4.5)

    # We only claim resolution when confidence is reasonably strong.
    resolved = confidence >= 0.38
    summary = re.sub(r"\s+", " ", content).strip()[:500] if resolved else ""
    excerpt = content[:1200] if resolved else ""

    return ContextResolution(
        has_reference=True,
        resolved=resolved,
        referent_summary=summary,
        source_message_index=idx if resolved else None,
        confidence=round(confidence, 3),
        context_excerpt=excerpt,
    )
