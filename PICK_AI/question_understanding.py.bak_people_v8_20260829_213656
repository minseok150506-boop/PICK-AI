from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from coding_assistant import is_coding_query
from web_search_engine import should_search


COMMON_KO_FIXES = {
    "안돼": "안 돼",
    "안되": "안 돼",
    "안됌": "안 됨",
    "어떻해": "어떻게",
    "어케": "어떻게",
    "뭐야": "무엇인가요",
    "왜안돼": "왜 안 돼",
    "왜 안되": "왜 안 돼",
    "실행안돼": "실행이 안 돼",
    "로그인안돼": "로그인이 안 돼",
    "버튼안눌려": "버튼이 안 눌려",
    "새채팅": "새 채팅",
    "체팅": "채팅",
    "랜더": "Render",
    "깃허브": "GitHub",
    "올라마": "Ollama",
    "파워셸": "PowerShell",
    "파워쉘": "PowerShell",
    "시놀로지": "Synology",
    "내일날씨": "내일 날씨",
    "오늘날씨": "오늘 날씨",
    "모레날씨": "모레 날씨",
    "날씨알려줘": "날씨 알려줘",
    "계속해줘": "계속 해줘",
    "풍양": "풍향",
    "바람방향": "바람 방향",
    "네비게이션": "내비게이션",
    "프라이전체이션": "프레젠테이션",
    "프리젠테이션": "프레젠테이션",
    "우편 번호": "우편번호",
}

REFERENCE_WORDS = [
    "이거", "그거", "저거", "이것", "그것", "저것",
    "아까", "전에", "위에", "그 파일", "그 코드", "그 버튼",
    "그 사이트", "그 주소", "그 설정", "그 명령어", "그 모델",
    "계속", "다음", "그대로", "이대로", "이것도", "그것도", "아까 거", "아까거",
]

ERROR_HINTS = [
    "에러", "오류", "안 돼", "안됨", "실패", "exception", "traceback",
    "error", "failed", "not found", "timeout", "connection refused",
]

QUESTION_HINTS = [
    "왜", "어떻게", "뭐", "무엇", "언제", "어디", "누가", "가능",
    "알려", "해줘", "해 줘", "찾아", "고쳐", "만들어",
]


@dataclass
class QuestionAnalysis:
    original: str
    normalized: str
    intent: str
    needs_web: bool
    coding: bool
    error_report: bool
    refers_to_context: bool
    ambiguity_score: int
    should_clarify: bool
    clarification_reason: str
    key_terms: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_question(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(r"\s+", " ", value)

    # Apply only conservative corrections. Do not rewrite product names or code.
    lowered = value.lower()
    for wrong, right in COMMON_KO_FIXES.items():
        if wrong in lowered:
            # preserve casing elsewhere by doing case-insensitive replacement
            value = re.sub(re.escape(wrong), right, value, flags=re.I)
            lowered = value.lower()

    # In weather/wind context, users often type 풍량 when they mean 풍향 (wind direction).
    if "풍량" in value and any(k in value for k in ("바람", "날씨", "방향", "몇 도")):
        value = value.replace("풍량", "풍향")

    # Normalize repeated punctuation/spacing without altering code-like content.
    value = re.sub(r"[?]{2,}", "?", value)
    value = re.sub(r"[!]{2,}", "!", value)
    return value.strip()


def extract_key_terms(text: str) -> list[str]:
    # Keep technical identifiers intact where possible.
    tokens = re.findall(
        r"[A-Za-z][A-Za-z0-9_.:+#/-]{1,}|[가-힣]{2,}|[\u4e00-\u9fff]{2,}|[\u3040-\u30ff]{2,}",
        text
    )
    stop = {
        "이거", "그거", "저거", "해줘", "해주세요", "알려줘", "어떻게",
        "무엇인가요", "왜", "그리고", "근데", "그런데", "가능",
    }
    out = []
    seen = set()
    for token in tokens:
        if token.lower() in stop or token in stop:
            continue
        key = token.lower()
        if key not in seen:
            seen.add(key)
            out.append(token)
        if len(out) >= 12:
            break
    return out


def classify_intent(text: str) -> str:
    t = text.lower()

    if any(x in t for x in ["우편번호", "zipcode", "zip code", "postal code"]):
        return "postal"
    if any(x in t for x in ["네비", "내비", "내비게이션", "길찾기", "이동 시간", "도착 시간"]) or ("까지" in t and any(x in t for x in ["몇 분", "몇분", "차로", "도보", "걸어서", "자전거"])):
        return "navigation"
    if any(x in t for x in ["ppt", "pptx", "파워포인트", "프레젠테이션", "엑셀", "xlsx", "워드", "docx"]):
        if any(x in t for x in ["만들", "생성", "작성", "제작", "파일로"]):
            return "office_file"

    if is_coding_query(text):
        if any(x in t for x in ERROR_HINTS):
            return "debug_code"
        if any(x in t for x in ["만들어", "작성", "구현", "코드"]):
            return "write_code"
        return "coding"

    if any(x in t for x in ["몇 시", "몇시", "현재 시간", "지금 시간", "시간 알려", "오늘 날짜", "무슨 요일"]):
        return "time"
    if any(x in t for x in ["날씨", "기온", "온도"]):
        return "weather"
    if "뉴스" in t:
        return "news"
    if "유튜브" in t or "youtube" in t:
        return "youtube"
    if any(x in t for x in ["가격", "파는", "판매", "재고", "구매"]):
        return "shopping_search"
    if any(x in t for x in ["에러", "오류", "안 돼", "안됨", "실패"]):
        return "troubleshoot"
    if any(x in t for x in ["번역", "translate"]):
        return "translate"
    if any(x in t for x in ["요약", "정리"]):
        return "summarize"
    if any(x in t for x in ["만들어", "해줘", "해 줘", "작성"]):
        return "create_or_modify"
    if any(x in t for x in QUESTION_HINTS):
        return "question"
    return "conversation"


def analyze_question(text: str, history: list[dict] | None = None) -> QuestionAnalysis:
    history = history or []
    original = str(text or "").strip()
    normalized = normalize_question(original)
    lowered = normalized.lower()

    coding = is_coding_query(normalized)
    error_report = any(x in lowered for x in ERROR_HINTS)
    refers = any(x in normalized for x in REFERENCE_WORDS)
    needs_web = should_search(normalized)

    ambiguity = 0
    reasons = []

    # Very short context-dependent utterances are ambiguous only if history cannot resolve them.
    if len(normalized) <= 6:
        ambiguity += 2
        reasons.append("질문이 매우 짧습니다.")

    if refers:
        ambiguity += 2
        reasons.append("이전 대상을 가리키는 표현이 있습니다.")

    # Error reports without any technical anchor may need clarification.
    terms = extract_key_terms(normalized)
    if error_report and not terms:
        ambiguity += 2
        reasons.append("오류 대상이나 오류 메시지가 없습니다.")

    # If there is recent context, lower ambiguity for references/short followups.
    recent = history[-6:]
    if recent:
        context_text = " ".join(str(m.get("content", "")) for m in recent)
        if refers or len(normalized) <= 6:
            if len(context_text.strip()) > 20:
                ambiguity = max(0, ambiguity - 2)
                reasons.append("최근 대화 문맥으로 일부 보완 가능합니다.")

    followup_phrases = {
        "해줘", "해 줘", "그렇게 해줘", "그렇게 해 줘", "계속", "계속해줘",
        "다음", "그대로", "이대로", "그거", "그것도", "이것도", "아까 거", "아까거",
    }
    if normalized in followup_phrases and recent:
        ambiguity = 0

    detected_intent = classify_intent(normalized)
    if detected_intent in {"weather", "time", "news", "coding", "write_code", "debug_code", "translate", "summarize", "postal", "navigation", "office_file"}:
        ambiguity = max(0, ambiguity - 2)

    should_clarify = ambiguity >= 3

    return QuestionAnalysis(
        original=original,
        normalized=normalized,
        intent=classify_intent(normalized),
        needs_web=needs_web,
        coding=coding,
        error_report=error_report,
        refers_to_context=refers,
        ambiguity_score=ambiguity,
        should_clarify=should_clarify,
        clarification_reason=" ".join(reasons),
        key_terms=terms,
    )


def build_understanding_instruction(analysis: QuestionAnalysis) -> str:
    terms = ", ".join(analysis.key_terms) if analysis.key_terms else "없음"
    return f"""[Question understanding]
Original user message: {analysis.original}
Normalized meaning: {analysis.normalized}
Detected intent: {analysis.intent}
Key terms: {terms}
Needs fresh web information: {"yes" if analysis.needs_web else "no"}
Coding request: {"yes" if analysis.coding else "no"}
Error/troubleshooting request: {"yes" if analysis.error_report else "no"}
Context-dependent reference: {"yes" if analysis.refers_to_context else "no"}

Response rules:
- Answer the user's actual intent, not merely individual keywords.
- Use recent conversation context to resolve phrases like "this", "that", or "do it".
- Do not rename product names, model names, filenames, code identifiers, URLs, or error messages.
- Do not ask a follow-up question when the answer can reasonably be inferred from the recent conversation.
- Ask one concise clarification only when a missing fact materially prevents a correct answer.
- If the user reports an error, prioritize the exact error text and the most recent relevant configuration.
- If current information is required, use web results and do not guess.
"""
