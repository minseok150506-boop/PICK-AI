
"""
PICK Engine
대화 분류, 상태 기억, 계획 생성, 도구 라우팅, 답변 검수를 담당하는 로컬 엔진입니다.
외부 API 없이 동작하도록 설계되었습니다.
"""

import re
import ast
import operator as op

_ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

SITE_RECOMMENDATIONS = {
    "이미지": [
        {"name": "Unsplash", "url": "https://unsplash.com", "desc": "무료 고품질 사진 사이트"},
        {"name": "Pexels", "url": "https://www.pexels.com", "desc": "무료 사진과 영상 사이트"},
        {"name": "Pixabay", "url": "https://pixabay.com", "desc": "무료 이미지, 벡터, 영상 제공"},
    ],
    "ppt": [
        {"name": "Slidesgo", "url": "https://slidesgo.com", "desc": "PPT 템플릿 사이트"},
        {"name": "Canva", "url": "https://www.canva.com", "desc": "디자인과 발표자료 제작"},
        {"name": "Beautiful.ai", "url": "https://www.beautiful.ai", "desc": "AI 기반 발표자료 제작"},
    ],
    "코딩": [
        {"name": "W3Schools", "url": "https://www.w3schools.com", "desc": "기초 코딩 학습"},
        {"name": "MDN", "url": "https://developer.mozilla.org", "desc": "웹 개발 공식 문서"},
        {"name": "GitHub", "url": "https://github.com", "desc": "코드 저장소와 오픈소스"},
    ],
    "게임에셋": [
        {"name": "itch.io", "url": "https://itch.io/game-assets", "desc": "게임 에셋 자료"},
        {"name": "Kenney", "url": "https://kenney.nl/assets", "desc": "무료 게임 에셋"},
        {"name": "OpenGameArt", "url": "https://opengameart.org", "desc": "오픈 게임 아트 자료"},
    ],
}

def default_state():
    return {
        "task": None,
        "topic": None,
        "options": {},
        "mode": "idle",
        "summary": "현재 진행 중인 작업 없음",
        "history": [],
        "last_intent": None,
        "last_plan": [],
        "last_tool": None,
    }

def update_history(state, role, content, limit=30):
    state.setdefault("history", [])
    state["history"].append({"role": role, "content": content})
    if len(state["history"]) > limit:
        state["history"] = state["history"][-limit:]

def summarize_state(state):
    task = state.get("task")
    topic = state.get("topic")
    options = state.get("options", {})
    if not task:
        return "현재 진행 중인 작업 없음"

    parts = [f"작업={task}"]
    if topic:
        parts.append(f"주제={topic}")

    shown = []
    for k, v in options.items():
        if v not in [None, False, "", {}]:
            shown.append(f"{k}={v}")
    if shown:
        parts.append("옵션=" + ", ".join(shown))

    return " / ".join(parts)

def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("지원하지 않는 수식입니다.")

def try_calculate(text):
    raw = (text or "").strip()
    lowered = raw.lower()

    expr = raw
    for p in ["계산해줘", "계산", "연산", "solve", "calc"]:
        if lowered.startswith(p):
            expr = raw[len(p):].strip()
            break

    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**").replace(" ", "")
    if not expr:
        return None

    if not re.fullmatch(r"[0-9\.\+\-\*\/%\(\)]{1,200}", expr):
        return None

    try:
        parsed = ast.parse(expr, mode="eval")
        result = _safe_eval(parsed.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"계산 결과는 {result} 입니다."
    except Exception:
        return "수식을 계산하지 못했습니다. 예: 12*(3+4)/2"

def extract_topic_for_ppt(text):
    cleaned = re.sub(
        r"ppt|피피티|프레젠테이션|발표자료|만들어줘|만들기|만들어|작성해줘|생성해줘|준비해줘",
        " ",
        text or "",
        flags=re.I,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or ""

def extract_slide_count(text):
    m = re.search(r"(\d+)\s*장", text or "")
    return int(m.group(1)) if m else None

def recommend_sites(text):
    lowered = (text or "").lower()
    if not any(k in text for k in ["사이트", "추천", "찾아", "알려"]):
        return []

    if "이미지" in text or "사진" in text:
        return SITE_RECOMMENDATIONS["이미지"]
    if "ppt" in lowered or "피피티" in text or "발표" in text or "템플릿" in text:
        return SITE_RECOMMENDATIONS["ppt"]
    if "코딩" in text or "프로그래밍" in text or "개발" in text:
        return SITE_RECOMMENDATIONS["코딩"]
    if "게임" in text and ("에셋" in text or "asset" in lowered):
        return SITE_RECOMMENDATIONS["게임에셋"]
    return []

def classify_intent(text, state):
    t = (text or "").strip()
    lowered = t.lower()

    if not t:
        return "empty"
    if try_calculate(t):
        return "calc"
    if "사이트" in t and any(x in t for x in ["추천", "찾아", "알려"]):
        return "site_recommend"
    if any(x in lowered for x in ["ppt", "피피티", "프레젠테이션"]) and any(x in t for x in ["만들", "생성", "작성", "준비"]):
        return "ppt_start"
    if state.get("task") == "ppt" and any(x in t for x in ["장", "이미지", "사진", "제목", "만들어", "생성", "저장", "파일", "그거", "이거", "아까", "계속"]):
        return "ppt_edit"
    if "이미지" in t and any(x in t for x in ["분석", "열어", "화면", "기능"]):
        return "image_tool"
    if ("동영상" in t or "영상" in t) and any(x in t for x in ["분석", "열어", "화면", "기능"]):
        return "video_tool"
    if "파일" in t and any(x in t for x in ["분석", "열어", "화면", "기능"]):
        return "file_tool"
    if ("exe" in lowered or "실행파일" in t) and any(x in t for x in ["만들", "열어", "기능", "도우미"]):
        return "exe_tool"
    if any(x in t for x in ["생각해서", "단계적으로", "정리해서", "검토해서", "설명", "왜", "이유", "어떻게", "비교", "차이", "요약", "정리"]):
        return "thinking_chat"
    return "chat"

def need_clarification(intent, text, state):
    if intent == "ppt_start" and not extract_topic_for_ppt(text):
        return "PPT 주제를 먼저 말씀해 주세요."
    if intent == "ppt_edit" and state.get("task") != "ppt":
        return "현재 진행 중인 PPT 작업이 없습니다. 먼저 주제를 말씀해 주세요."
    if any(x in (text or "") for x in ["그거", "이거", "아까", "계속"]) and not state.get("task"):
        return "무엇을 이어서 처리할지 먼저 말씀해 주세요."
    return None

def make_plan(intent):
    plans = {
        "calc": ["수식 추출", "안전 계산", "결과 반환"],
        "site_recommend": ["주제 파악", "추천 목록 선택", "링크 반환"],
        "ppt_start": ["주제 추출", "PPT 상태 저장", "장수와 이미지 여부 확인"],
        "ppt_edit": ["현재 PPT 상태 확인", "옵션 수정", "생성 여부 판단"],
        "image_tool": ["이미지 분석 화면 열기"],
        "video_tool": ["동영상 분석 화면 열기"],
        "file_tool": ["파일 분석 화면 열기"],
        "exe_tool": ["EXE 도우미 화면 열기"],
        "thinking_chat": ["질문 핵심 파악", "답변 구조화", "짧고 분명하게 설명"],
    }
    return plans.get(intent, ["일반 대화 처리"])

def choose_tool(intent):
    return {
        "calc": "calculator",
        "site_recommend": "site_recommend",
        "ppt_start": "ppt",
        "ppt_edit": "ppt",
        "image_tool": "image_ui",
        "video_tool": "video_ui",
        "file_tool": "file_ui",
        "exe_tool": "exe_ui",
        "thinking_chat": "reasoning",
        "chat": "chat",
        "empty": "chat",
    }.get(intent, "chat")

def simple_reasoned_reply(text):
    if "누구" in text and ("너" in text or "PICK" in text.upper()):
        return "저는 PICK입니다. 질문에 답하고, PPT·파일·이미지·동영상·계산·추천 같은 작업을 도와주는 챗봇입니다."
    if "호랑이" in text:
        return "호랑이는 고양이과에 속하는 대형 맹수입니다. 줄무늬, 강한 턱, 단독 생활, 높은 사냥 능력이 대표 특징입니다."
    if "비교" in text:
        return "비교할 두 대상을 말씀해 주시면 차이점을 표처럼 정리해 드리겠습니다."
    if "왜" in text or "이유" in text:
        return "원인을 설명하려면 대상이 필요합니다. 무엇에 대한 이유인지 조금 더 구체적으로 말씀해 주세요."
    return "질문을 이해했습니다. 더 구체적으로 말씀해 주시면 정확하게 정리해 드리겠습니다."

def build_structured_answer(text, state):
    return (
        f"요청 이해: {text}\n"
        f"현재 상태: {summarize_state(state)}\n"
        "처리 계획:\n"
        "1. 질문의 핵심을 정리합니다.\n"
        "2. 필요한 내용을 구조화합니다.\n"
        "3. 핵심만 분명하게 설명합니다.\n\n"
        f"결과: {simple_reasoned_reply(text)}"
    )

def local_chat_reply(text, username):
    if not text:
        return "말씀을 입력해 주세요."
    if "안녕" in text:
        return "안녕하세요. 무엇을 도와드릴까요?"
    if "이름" in text:
        return f"현재 로그인한 아이디는 {username} 입니다."
    return simple_reasoned_reply(text)

def review_reply(reply, state):
    if not reply or not reply.strip():
        return "응답을 만들지 못했습니다."
    for bad in ["이어서 진행하겠습니다", '말씀하신 "']:
        if bad in reply:
            return "질문을 이해했습니다. 조금 더 구체적으로 말씀해 주세요."
    if state.get("task") == "ppt":
        slides = state.get("options", {}).get("slides")
        if not slides and "몇 장" not in reply and "장으로" not in reply:
            return reply + "\n\n몇 장으로 만들지도 말씀해 주세요."
    return reply

class PickEngine:
    def __init__(self):
        self.states = {}

    def get_state(self, user_id):
        if user_id not in self.states:
            self.states[user_id] = default_state()
        return self.states[user_id]

    def handle(self, text, username, user_id, tools):
        state = self.get_state(user_id)
        update_history(state, "user", text)

        intent = classify_intent(text, state)
        state["last_intent"] = intent
        state["last_plan"] = make_plan(intent)
        state["last_tool"] = choose_tool(intent)

        clarification = need_clarification(intent, text, state)
        if clarification:
            update_history(state, "assistant", clarification)
            return {"reply": clarification}

        result = self.execute(intent, text, username, user_id, state, tools)
        result["reply"] = review_reply(result.get("reply", ""), state)

        state["summary"] = summarize_state(state)
        update_history(state, "assistant", result["reply"])
        return result

    def execute(self, intent, text, username, user_id, state, tools):
        if intent == "empty":
            return {"reply": "말씀을 입력해 주세요."}

        if intent == "calc":
            return {"reply": try_calculate(text)}

        if intent == "site_recommend":
            sites = recommend_sites(text)
            if not sites:
                return {"reply": "해당 주제에 맞는 추천 사이트를 찾지 못했습니다."}
            reply = "추천 사이트입니다.\n\n"
            for s in sites:
                reply += f"{s['name']}\n{s['desc']}\n{s['url']}\n\n"
            return {"reply": reply}

        if intent == "ppt_start":
            topic = extract_topic_for_ppt(text)
            state["task"] = "ppt"
            state["topic"] = topic
            state["options"] = {"slides": None, "image": False, "title": topic}
            state["mode"] = "working"
            return {"reply": f'"{topic}" PPT 작업을 시작했습니다. 몇 장으로 만들까요? 이미지 포함 여부도 말씀해 주세요.'}

        if intent == "ppt_edit":
            return self._handle_ppt_edit(text, state, tools)

        if intent == "image_tool":
            return {"reply": "이미지 분석 화면을 열겠습니다.", "ui_action": "open_image"}
        if intent == "video_tool":
            return {"reply": "동영상 분석 화면을 열겠습니다.", "ui_action": "open_video"}
        if intent == "file_tool":
            return {"reply": "파일 분석 화면을 열겠습니다.", "ui_action": "open_file"}
        if intent == "exe_tool":
            return {"reply": "EXE 도우미 화면을 열겠습니다.", "ui_action": "open_exe"}
        if intent == "thinking_chat":
            llm = tools.get("llm") if isinstance(tools, dict) else None
            if llm:
                try:
                    answer = llm.generate(text, state=state, history=state.get("history", []))
                    return {"reply": (
                        f"요청 이해: {text}\n"
                        f"현재 상태: {summarize_state(state)}\n"
                        "처리 계획:\n"
                        "1. 질문의 핵심을 정리합니다.\n"
                        "2. 필요한 내용을 구조화합니다.\n"
                        "3. 핵심만 분명하게 답합니다.\n\n"
                        f"결과: {answer}"
                    )}
                except Exception:
                    return {"reply": build_structured_answer(text, state)}
            return {"reply": build_structured_answer(text, state)}

        llm = tools.get("llm") if isinstance(tools, dict) else None
        if llm:
            try:
                return {"reply": llm.generate(text, state=state, history=state.get("history", []))}
            except Exception:
                pass

        return {"reply": local_chat_reply(text, username)}

    def _handle_ppt_edit(self, text, state, tools):
        if state.get("task") != "ppt":
            return {"reply": "현재 진행 중인 PPT 작업이 없습니다. 먼저 주제를 말씀해 주세요."}

        slide_count = extract_slide_count(text)
        if slide_count:
            state["options"]["slides"] = slide_count
            return {"reply": f"슬라이드를 {slide_count}장으로 설정했습니다."}

        if "이미지" in text or "사진" in text:
            state["options"]["image"] = True
            return {"reply": "이미지 포함으로 반영했습니다."}

        if "제목" in text and any(x in text for x in ["바꿔", "변경"]):
            title = text.replace("제목", "").replace("바꿔줘", "").replace("변경", "").strip()
            if title:
                state["options"]["title"] = title
                return {"reply": f'제목을 "{title}"로 반영했습니다.'}
            return {"reply": "제목 변경 요청을 반영했습니다."}

        if any(x in text for x in ["만들어", "생성", "저장", "파일"]):
            topic = state.get("topic") or "주제"
            options = state.get("options", {})
            if not options.get("slides"):
                return {"reply": "몇 장으로 만들지 먼저 말씀해 주세요."}
            try:
                filename = tools["create_ppt"](topic, options)
            except Exception:
                return {"reply": "PPT 생성 중 문제가 생겼습니다. 제목이나 장수를 다시 확인해 주세요."}
            state["mode"] = "done"
            return {"reply": f'"{topic}" PPT 생성을 완료했습니다.', "ppt_filename": filename}

        if any(x in text for x in ["그거", "이거", "아까", "계속"]):
            return {"reply": f'현재 "{state.get("topic")}" PPT 작업 중입니다. 장수, 제목, 이미지 여부, 생성 여부를 말씀해 주세요.'}

        return {"reply": "PPT 옵션을 수정 중입니다. 장수, 제목, 이미지 여부, 생성 여부를 말씀해 주세요."}
