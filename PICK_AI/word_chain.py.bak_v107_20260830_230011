from __future__ import annotations

import json
import re
import urllib.request

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_FALLBACK_MODELS


_START_RE = re.compile(r"(끝말\s*잇기|끝말잇기)")
_HANGUL_WORD_RE = re.compile(r"^[가-힣]{2,}$")
_SINGLE_HANGUL_RE = re.compile(r"^[가-힣]$")
_STOP_WORDS = ("그만", "끝내", "종료", "끝말잇기 그만", "끝말잇기 종료")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _single_word(value: str) -> str | None:
    text = _clean(value)
    text = re.sub(r"^[\"'`“”‘’\(\[\{]+|[\"'`“”‘’\)\]\}\.!?,~:;]+$", "", text).strip()
    if re.fullmatch(r"[가-힣]+", text):
        return text
    return None


def _is_start_request(text: str) -> bool:
    value = _clean(text)
    if not _START_RE.search(value):
        return False
    return any(x in value for x in ("하자", "시작", "할래", "해보자")) or value in {
        "끝말잇기", "끝말 잇기"
    }


def _game_start_index(history: list[dict]) -> int | None:
    idx = None
    for i, item in enumerate(history or []):
        if str(item.get("role") or "") != "user":
            continue
        content = _clean(item.get("content") or "")
        if _is_start_request(content):
            idx = i
        elif idx is not None and content in _STOP_WORDS:
            idx = None
    return idx


def _game_active(history: list[dict]) -> bool:
    return _game_start_index(history) is not None


def _game_words(history: list[dict]) -> list[str]:
    start = _game_start_index(history)
    if start is None:
        return []
    words = []
    for item in history[start + 1:]:
        word = _single_word(item.get("content") or "")
        if word and len(word) >= 2:
            words.append(word)
    return words


def _last_assistant_word(history: list[dict]) -> str | None:
    start = _game_start_index(history)
    if start is None:
        return None
    for item in reversed(history[start + 1:]):
        if str(item.get("role") or "") not in {"assistant", "bot"}:
            continue
        word = _single_word(item.get("content") or "")
        if word and len(word) >= 2:
            return word
    return None


def _candidate_from_text(text: str, required_start: str, used: set[str]) -> str | None:
    raw = str(text or "")
    direct = _single_word(raw)
    candidates = [direct] if direct else re.findall(r"[가-힣]{2,}", raw)
    for word in candidates:
        if not word:
            continue
        if len(word) < 2:
            continue
        if not _HANGUL_WORD_RE.fullmatch(word):
            continue
        if not word.startswith(required_start):
            continue
        if word in used:
            continue
        if "끝말잇기" in word:
            continue
        return word
    return None


def _model_candidates() -> list[str]:
    out = []
    for model in [OLLAMA_MODEL, *OLLAMA_FALLBACK_MODELS]:
        if model and model not in out:
            out.append(model)
    return out[:4]


def _ask_model(required_start: str, used: set[str], attempt: int) -> str:
    used_text = ", ".join(sorted(used)[-80:]) if used else "없음"
    prompt = f"""/no_think
한국어 끝말잇기에서 PICK이 낼 단어 하나만 출력하세요.

필수 규칙:
1. 반드시 '{required_start}' 글자로 시작해야 합니다.
2. 반드시 한글 2글자 이상의 일반적인 명사 한 단어여야 합니다.
3. 한 글자 단어는 절대 금지입니다.
4. 설명, 문장, 따옴표, 번호, 마침표를 붙이지 마세요.
5. 이미 사용한 단어는 다시 쓰지 마세요.
6. 사람 이름, 임의의 글자 조합, 존재하지 않는 단어는 쓰지 마세요.

이미 사용한 단어:
{used_text}

이번 시도 번호: {attempt}

정답 단어 하나만 출력:
"""
    last_error = None
    for model in _model_candidates():
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.15,
                "top_p": 0.85,
                "num_ctx": 2048,
                "num_predict": 24,
            },
        }
        req = urllib.request.Request(
            OLLAMA_HOST.rstrip("/") + "/api/generate",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            text = str(data.get("response") or "").strip()
            if text:
                return text
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise RuntimeError(str(last_error))
    return ""


_FALLBACK = {
    "과": ["과자", "과일", "과학"],
    "자": ["자동차", "자전거", "자석"],
    "차": ["차표", "차량", "차고"],
    "표": ["표범", "표정", "표지"],
    "범": ["범선", "범인", "범위"],
    "선": ["선물", "선풍기", "선생님"],
    "물": ["물고기", "물감", "물병"],
    "기": ["기차", "기린", "기쁨"],
    "린": ["린스"],
    "스": ["스키", "스위치", "스피커"],
    "키": ["키보드", "키위", "키다리"],
    "드": ["드라마", "드레스", "드럼"],
    "마": ["마음", "마차", "마늘"],
    "음": ["음악", "음료", "음식"],
    "악": ["악기", "악수", "악보"],
    "수": ["수박", "수건", "수영"],
    "박": ["박물관", "박수", "박쥐"],
    "관": ["관광", "관찰", "관문"],
    "광": ["광고", "광산", "광장"],
    "고": ["고양이", "고래", "고무"],
    "이": ["이불", "이름", "이야기"],
    "불": ["불꽃", "불빛", "불고기"],
    "꽃": ["꽃병", "꽃밭", "꽃잎"],
    "병": ["병원", "병아리", "병풍"],
    "원": ["원숭이", "원룸", "원칙"],
    "숭": ["숭어"],
    "어": ["어깨", "어묵", "어항"],
    "항": ["항구", "항공", "항아리"],
    "구": ["구름", "구두", "구슬"],
    "두": ["두부", "두꺼비", "두루미"],
    "부": ["부엌", "부채", "부모"],
    "채": ["채소", "채점", "채널"],
    "소": ["소나무", "소금", "소풍"],
    "풍": ["풍선", "풍경", "풍차"],
    "장": ["장미", "장갑", "장난감"],
    "미": ["미로", "미소", "미역"],
    "로": ["로봇", "로켓", "로션"],
    "봇": ["봇물"],
    "거": ["거울", "거리", "거미"],
    "울": ["울타리", "울음", "울림"],
    "리": ["리본", "리듬", "리더"],
    "본": ["본능", "본사", "본체"],
    "능": ["능력", "능선", "능률"],
    "인": ["인형", "인사", "인구"],
    "형": ["형광등", "형식", "형제"],
    "식": ["식당", "식물", "식탁"],
    "당": ["당근", "당첨", "당일"],
    "근": ["근육", "근처", "근무"],
    "육": ["육상", "육교", "육지"],
    "상": ["상자", "상어", "상상"],
    "깨": ["깨소금", "깨달음"],
    "금": ["금요일", "금속", "금메달"],
    "속": ["속담", "속도", "속옷"],
    "담": ["담요", "담장", "담배"],
    "요": ["요리", "요금", "요정"],
    "정": ["정답", "정원", "정리"],
    "답": ["답장", "답변", "답안"],
}


def _pick_next_word(required_start: str, used: set[str]) -> str | None:
    for word in _FALLBACK.get(required_start, []):
        if word not in used and len(word) >= 2 and _HANGUL_WORD_RE.fullmatch(word):
            return word

    for attempt in range(1, 4):
        try:
            raw = _ask_model(required_start, used, attempt)
        except Exception:
            raw = ""
        candidate = _candidate_from_text(raw, required_start, used)
        if candidate:
            return candidate
    return None


def handle_word_chain(text: str, history: list[dict]) -> str | None:
    current = _clean(text)

    if _is_start_request(current):
        return "사과"

    if not _game_active(history):
        return None

    if current in _STOP_WORDS or current in {"그만할래", "여기까지"}:
        return "끝말잇기를 종료할게요."

    user_word = _single_word(current)
    if user_word is None:
        return "끝말잇기에서는 한글 단어 하나만 말해 주세요."

    if _SINGLE_HANGUL_RE.fullmatch(user_word) or len(user_word) < 2:
        return "한 글자 단어는 안 돼요. 두 글자 이상인 단어를 말해 주세요."

    used = set(_game_words(history))
    previous = _last_assistant_word(history)

    if previous:
        required = previous[-1]
        if not user_word.startswith(required):
            return f"'{previous}'의 마지막 글자는 '{required}'이에요. '{required}'으로 시작하는 두 글자 이상 단어를 말해 주세요."

    if user_word in used:
        return f"'{user_word}'은 이미 나온 단어예요. 다른 두 글자 이상 단어를 말해 주세요."

    used.add(user_word)
    required_start = user_word[-1]
    next_word = _pick_next_word(required_start, used)

    if next_word:
        return next_word

    return f"'{required_start}'으로 시작하는 규칙에 맞는 두 글자 이상 단어를 찾지 못했어요. 이번 판은 제가 졌어요!"
