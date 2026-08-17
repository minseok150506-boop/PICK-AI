
"""
PICK Response Polish

기능:
- 한국어 문장 후처리
- 어색한 표현 정리
- 영어 섞임 완화
- 답변 검수
- 생각 모드 표시용 포맷
"""

import re


BAD_PHRASES = {
    "무엇을 도와드릴까요?": "어떤 부분을 도와드릴까요?",
    "말씀해 주시면 정확하게 도와드리겠습니다.": "필요한 내용을 말씀해 주시면 정확히 도와드리겠습니다.",
    "더 구체적으로 말씀해 주시면 정확하게 도와드리겠습니다.": "조금 더 구체적으로 말씀해 주시면 정확히 도와드리겠습니다.",
    "요청을 이해했습니다.": "요청을 확인했습니다.",
    "알겠습니다.": "확인했습니다.",
    "이어서 진행하겠습니다.": "현재 작업 흐름을 확인했습니다.",
}


def is_korean_text(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text or "")


def polish_korean(text: str) -> str:
    if not text:
        return "응답을 만들지 못했습니다. 다시 한 번 말씀해 주세요."

    t = str(text).strip()
    t = t.replace("\r\n", "\n").replace("\r", "\n")

    # 반복 공백 정리
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)

    # 어색한 고정 문구 정리
    for bad, good in BAD_PHRASES.items():
        t = t.replace(bad, good)

    # 영어 시작 답변 방지
    english_starts = ["Sure", "Okay", "Hello", "Looks like", "It seems", "I think"]
    if any(t.startswith(s) for s in english_starts):
        t = "한국어로 답변하겠습니다.\n\n" + t

    # 문장 끝 정리
    if len(t) > 0 and not t.endswith((".", "!", "?", "요.", "다.", "니다.", "세요.", "습니다.", "입니다.", "드립니다.", "함.")):
        t += "."

    return t


def make_thinking_block(user_text: str, intent: str = "", state_summary: str = "") -> str:
    intent_label = intent or "일반 대화"
    state = state_summary or "현재 진행 중인 작업 없음"

    return (
        "생각 모드\n"
        f"- 요청 이해: {user_text}\n"
        f"- 의도 판단: {intent_label}\n"
        f"- 현재 상태: {state}\n"
        "- 처리 계획: 필요한 정보를 확인하고, 가장 적절한 기능 또는 답변 방식으로 처리합니다.\n"
    )


def final_review(reply: str, user_text: str = "", intent: str = "", state_summary: str = "", thinking: bool = False) -> str:
    answer = polish_korean(reply)

    if thinking:
        return make_thinking_block(user_text, intent, state_summary) + "\n결과\n" + answer

    return answer
