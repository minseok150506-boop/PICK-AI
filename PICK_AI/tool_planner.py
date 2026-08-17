from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class RoutePlan:
    primary: str
    use_web: bool
    use_memory: bool
    use_coding: bool
    use_vision: bool
    use_file_analysis: bool
    clarify_first: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def plan_route(analysis, context_resolution=None) -> RoutePlan:
    intent = getattr(analysis, "intent", "question")
    coding = bool(getattr(analysis, "coding", False))
    needs_web = bool(getattr(analysis, "needs_web", False))
    should_clarify = bool(getattr(analysis, "should_clarify", False))

    if context_resolution and context_resolution.resolved:
        should_clarify = False

    primary = "chat"
    reason = "일반 대화/질문 처리"

    if intent in {"debug_code", "write_code", "coding"}:
        primary = "coding"
        reason = "코딩 요청으로 분류됨"
    elif intent == "weather":
        primary = "weather"
        needs_web = True
        reason = "실시간 날씨 정보 필요"
    elif intent == "news":
        primary = "news"
        needs_web = True
        reason = "최신 뉴스 정보 필요"
    elif intent in {"youtube", "shopping_search"}:
        primary = "web_search"
        needs_web = True
        reason = "실시간 검색 정보 필요"
    elif intent == "troubleshoot":
        primary = "troubleshoot"
        reason = "오류/문제 해결 요청"
    elif intent == "translate":
        primary = "translation"
        reason = "번역 요청"
    elif intent == "summarize":
        primary = "summarization"
        reason = "요약 요청"

    return RoutePlan(
        primary=primary,
        use_web=needs_web,
        use_memory=True,
        use_coding=coding,
        use_vision=False,
        use_file_analysis=False,
        clarify_first=should_clarify,
        reason=reason,
    )
