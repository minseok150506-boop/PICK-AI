from __future__ import annotations

import re


def _followup_mode(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    plain = value.rstrip("?!.")

    if plain.startswith("왜") or plain == "이유는":
        return "reason"
    if plain.startswith("어떻게") or plain.startswith("방법"):
        return "method"
    if (
        plain.startswith("더")
        or plain.startswith("자세히")
        or plain.startswith("계속")
    ):
        return "expand"
    if plain in {"진짜", "정말", "맞아"}:
        return "verify"
    if plain.startswith(("그럼", "그러면", "그래서")):
        return "continue"
    if plain in {
        "알려줘", "알려 주세요", "알려주세요",
        "말해줘", "말해 주세요",
        "답해줘", "답해 주세요",
        "설명해줘", "설명해 주세요",
        "해줘", "해 줘", "해주세요",
        "추천해줘", "추천해 주세요",
        "내일은", "모레는", "오늘은",
        "가격은", "장점은", "단점은",
    }:
        return "fulfill"
    return "reference"


def rewrite_for_reasoning(analysis, context_resolution=None) -> str:
    base = (
        getattr(analysis, "normalized", "")
        or getattr(analysis, "original", "")
    )
    base = re.sub(r"\s+", " ", str(base)).strip()

    if (
        context_resolution
        and context_resolution.resolved
        and context_resolution.referent_summary
    ):
        mode = _followup_mode(base)

        instructions = {
            "fulfill": (
                "사용자의 현재 말은 직전 사용자 요청에 대한 답을 실제로 "
                "요구하는 후속 표현입니다. 같은 질문을 되묻지 말고 "
                "직전 사용자 요청에 구체적으로 직접 답하세요."
            ),
            "reason": (
                "사용자는 직전 대화 내용의 이유를 묻고 있습니다. "
                "직전 사용자 요청과 PICK 답변을 바탕으로 왜 그런지 "
                "직접 설명하세요."
            ),
            "method": (
                "사용자는 직전 주제의 방법이나 절차를 묻고 있습니다. "
                "이전 대상을 유지한 채 구체적인 방법을 설명하세요."
            ),
            "expand": (
                "사용자는 직전 주제를 더 자세히 이어서 설명해 달라는 "
                "뜻입니다. 주제를 바꾸거나 무엇을 원하는지 되묻지 말고 "
                "내용을 확장하세요."
            ),
            "verify": (
                "사용자는 직전 답변이 사실인지 확인하려는 뜻입니다. "
                "직전 주장을 검토해 명확하게 답하세요."
            ),
            "continue": (
                "사용자는 직전 주제를 이어서 묻고 있습니다. "
                "현재 짧은 표현을 이전 주제와 결합해 자연스럽게 답하세요."
            ),
            "reference": (
                "현재 메시지의 지시어가 가리키는 대상을 아래 이전 문맥에서 "
                "해석해 답하세요. 문맥으로 충분히 특정되면 되묻지 마세요."
            ),
        }

        return (
            f"{base}\n\n"
            "[Resolved previous context]\n"
            f"{context_resolution.referent_summary}\n\n"
            "[Resolved follow-up intent]\n"
            f"{instructions.get(mode, instructions['reference'])}"
        )

    return base


def build_clarification(analysis, context_resolution=None) -> str:
    intent = getattr(analysis, "intent", "question")
    reason = getattr(analysis, "clarification_reason", "")

    if (
        context_resolution
        and context_resolution.has_reference
        and not context_resolution.resolved
    ):
        return (
            "이전 대화에서 가리키는 대상을 찾지 못했습니다. "
            "어떤 내용을 이어서 말씀하신 건지만 짧게 알려주세요."
        )

    if intent in {"debug_code", "troubleshoot"}:
        return (
            "정확히 확인하려면 현재 보이는 오류 메시지와 "
            "문제가 발생한 파일 또는 화면을 알려주세요."
        )

    if reason:
        return (
            "정확히 답하려면 한 가지만 더 확인이 필요합니다. "
            f"{reason}"
        )

    return "정확히 답하려면 대상이나 원하는 결과를 한 가지 더 알려주세요."
