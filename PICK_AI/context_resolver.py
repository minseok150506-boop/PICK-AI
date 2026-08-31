from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


REFERENCE_TERMS = {
    "이거", "그거", "저거", "이것", "그것", "저것",
    "아까", "전에", "위에", "그 파일", "그 코드", "그 버튼",
    "그걸", "그걸로", "그렇게", "그 방법", "그 모델", "그 주소",
    "그 사이트", "그 설정", "그 명령어", "그대로", "이대로",
    "계속", "다음", "이것도", "그것도", "아까 거", "아까거",
    "그럼", "그러면", "그래서", "그건", "그게", "그런", "그 중", "그중",
}

IMPLICIT_FOLLOWUPS = {
    "알려줘", "알려 주세요", "알려주세요",
    "말해줘", "말해 주세요", "말해주세요",
    "답해줘", "답해 주세요", "답해주세요",
    "설명해줘", "설명해 주세요", "설명해주세요",
    "해줘", "해 줘", "해주세요", "해 주세요",
    "더 알려줘", "더 알려 주세요", "더 알려주세요",
    "더 자세히", "자세히", "자세히 알려줘",
    "계속", "계속해줘", "계속 해줘", "계속 알려줘",
    "다음", "다음은",
    "왜", "왜?", "왜 그래", "왜 그래?", "왜 그런거야", "왜 그런 거야",
    "어떻게", "어떻게?", "어떻게 해", "어떻게 해?", "방법은", "방법은?",
    "그럼", "그럼?", "그러면", "그러면?", "그래서", "그래서?",
    "진짜", "진짜?", "정말", "정말?", "맞아", "맞아?",
    "추천해줘", "추천해 주세요", "추천해주세요",
    "내일은", "내일은?", "모레는", "모레는?", "오늘은", "오늘은?",
    "가격은", "가격은?", "이유는", "이유는?",
    "장점은", "장점은?", "단점은", "단점은?",
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


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _followup_mode(message: str) -> str:
    value = _clean(message).lower()
    plain = value.rstrip("?!.")

    normalized_followups = {x.rstrip("?!.").lower() for x in IMPLICIT_FOLLOWUPS}
    if plain in normalized_followups:
        if plain.startswith("왜") or plain == "이유는":
            return "reason"
        if plain.startswith("어떻게") or plain.startswith("방법"):
            return "method"
        if plain.startswith("더") or plain.startswith("자세히") or plain.startswith("계속"):
            return "expand"
        if plain in {"진짜", "정말", "맞아"}:
            return "verify"
        if plain.startswith(("그럼", "그러면", "그래서")):
            return "continue"
        return "fulfill"

    if any(term in value for term in REFERENCE_TERMS):
        if "왜" in value or "이유" in value:
            return "reason"
        if "어떻게" in value or "방법" in value:
            return "method"
        if any(x in value for x in ("더", "자세히", "계속")):
            return "expand"
        return "reference"

    compact = re.sub(r"\s+", "", value)
    if len(compact) <= 12 and re.search(r"(은|는|도)\??$", compact):
        return "continue"

    return ""


def is_context_followup(message: str) -> bool:
    return bool(_followup_mode(message))


def _score_candidate(text: str, user_message: str, distance: int, role: str) -> float:
    score = 0.0
    t = text.lower()
    u = user_message.lower()

    technical = re.findall(
        r"[A-Za-z][A-Za-z0-9_.:+#/-]{2,}|[가-힣]{2,}",
        u
    )
    for token in technical:
        if token.lower() in t:
            score += 1.5

    if any(x in t for x in [
        "오류", "에러", "error", "exception",
        "파일", "버튼", "모델", "서버", "코드"
    ]):
        score += 0.8

    score += max(0.0, 1.8 - distance * 0.2)
    if role == "user":
        score += 0.7
    return score


def _recent_pair(history: list[dict]):
    recent = history[-20:]
    user_row = None
    assistant_row = None

    for rev_idx, item in enumerate(reversed(recent)):
        content = _clean(item.get("content") or "")
        if not content:
            continue

        idx = len(recent) - 1 - rev_idx
        role = str(item.get("role") or "")

        if user_row is None and role == "user":
            user_row = (idx, content)
        if assistant_row is None and role == "assistant":
            assistant_row = (idx, content)

        if user_row and assistant_row:
            break

    return user_row, assistant_row


def resolve_reference(
    user_message: str,
    history: list[dict] | None = None
) -> ContextResolution:
    history = history or []
    message = _clean(user_message)
    mode = _followup_mode(message)

    explicit_ref = any(term in message for term in REFERENCE_TERMS)
    has_ref = explicit_ref or bool(mode)

    if not has_ref:
        return ContextResolution(False, False, "", None, 0.0, "")

    if not history:
        return ContextResolution(True, False, "", None, 0.0, "")

    recent = history[-20:]
    user_row, assistant_row = _recent_pair(recent)

    # For short follow-ups, the previous USER request is the primary anchor.
    # This avoids adopting a weak assistant reply like "무엇을 알려드릴까요?"
    # as the user's actual intent.
    if mode and user_row:
        user_idx, user_text = user_row
        parts = [f"[직전 사용자 요청] {user_text}"]

        if mode in {
            "reason", "method", "expand",
            "verify", "continue", "reference"
        } and assistant_row:
            _, assistant_text = assistant_row
            parts.append(
                f"[직전 PICK 답변] {assistant_text[:700]}"
            )

        excerpt_rows = []
        for item in recent[-6:]:
            role = "사용자" if item.get("role") == "user" else "PICK"
            content = _clean(item.get("content") or "")
            if content:
                excerpt_rows.append(f"{role}: {content}")

        return ContextResolution(
            has_reference=True,
            resolved=True,
            referent_summary="\n".join(parts)[:1400],
            source_message_index=user_idx,
            confidence=0.96,
            context_excerpt="\n".join(excerpt_rows)[:2400],
        )

    candidates = []
    for rev_idx, item in enumerate(reversed(recent)):
        content = _clean(item.get("content") or "")
        if not content:
            continue
        role = str(item.get("role") or "")
        score = _score_candidate(content, message, rev_idx, role)
        candidates.append(
            (score, len(recent) - 1 - rev_idx, role, content)
        )

    if not candidates:
        return ContextResolution(True, False, "", None, 0.0, "")

    candidates.sort(key=lambda row: row[0], reverse=True)
    best_score, idx, role, content = candidates[0]
    confidence = min(1.0, best_score / 4.5)
    resolved = confidence >= 0.30

    if not resolved:
        return ContextResolution(
            True, False, "", None, round(confidence, 3), ""
        )

    label = (
        "직전 사용자 요청"
        if role == "user"
        else "직전 PICK 답변"
    )

    return ContextResolution(
        has_reference=True,
        resolved=True,
        referent_summary=f"[{label}] {content}"[:1400],
        source_message_index=idx,
        confidence=round(confidence, 3),
        context_excerpt=content[:2400],
    )
