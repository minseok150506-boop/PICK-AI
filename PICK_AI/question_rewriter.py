from __future__ import annotations

import re


def rewrite_for_reasoning(analysis, context_resolution=None) -> str:
    base = getattr(analysis, "normalized", "") or getattr(analysis, "original", "")
    base = re.sub(r"\s+", " ", str(base)).strip()

    if context_resolution and context_resolution.resolved and context_resolution.referent_summary:
        return (
            f"{base}\n\n"
            "[Resolved previous context]\n"
            f"{context_resolution.referent_summary}"
        )

    return base


def build_clarification(analysis, context_resolution=None) -> str:
    intent = getattr(analysis, "intent", "question")
    reason = getattr(analysis, "clarification_reason", "")

    if context_resolution and context_resolution.has_reference and not context_resolution.resolved:
        return "어떤 항목을 말씀하시는지 최근 대화만으로 확실히 특정하기 어렵습니다. 파일명, 버튼 이름, 오류 메시지 중 하나만 알려주세요."

    if intent in {"debug_code", "troubleshoot"}:
        return "정확히 확인하려면 현재 보이는 오류 메시지와 문제가 발생한 파일 또는 화면을 알려주세요."

    if reason:
        return f"정확히 답하려면 한 가지만 더 확인이 필요합니다. {reason}"

    return "정확히 답하려면 대상이나 원하는 결과를 한 가지 더 알려주세요."
