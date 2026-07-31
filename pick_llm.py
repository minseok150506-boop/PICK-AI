
import os
import json
import urllib.request


class PickLocalLLM:
    def generate(self, text, state=None, history=None):
        text = (text or "").strip()

        if any(k in text for k in ["너는 누구", "너 뭐야", "정체", "누가 만들"]):
            return "저는 PICK입니다. 질문에 답하고 여러 작업을 도와주는 로컬 AI 챗봇입니다."

        if "호랑이" in text:
            return "호랑이는 고양이과에 속하는 대형 맹수입니다. 줄무늬, 강한 턱, 단독 생활, 뛰어난 사냥 능력이 대표 특징입니다."

        if any(k in text for k in ["설명", "알려", "뭐야", "무엇", "왜", "이유"]):
            return "핵심부터 정리하겠습니다. 이 질문은 개념을 이해하고 중요한 특징을 나누어 답하는 방식이 좋습니다."

        return "요청을 이해했습니다. 더 구체적으로 말씀해 주시면 정확하게 도와드리겠습니다."



def _try_ollama_model(host, model, prompt, timeout):
    import json
    import urllib.request

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.35,
            "top_p": 0.85,
            "num_predict": 900
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=data,
        headers={
            "Content-Type": "application/json",
            **({"X-PICK-TUNNEL-TOKEN": os.environ.get("PICK_OLLAMA_TOKEN", "")} if os.environ.get("PICK_OLLAMA_TOKEN") else {}),
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = json.loads(res.read().decode("utf-8"))
        return (body.get("response") or "").strip()


class PickOllamaLLM:
    def __init__(self, model=None, host=None, timeout=120):
        self.model = model or os.environ.get("PICK_OLLAMA_MODEL", "qwen2.5:32b")
        self.host = (host or os.environ.get("PICK_OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.timeout = timeout

    def generate(self, text, state=None, history=None):
        prompt = self._build_prompt(text, state or {}, history or [])
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 800
            }
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as res:
            body = json.loads(res.read().decode("utf-8"))
            return (body.get("response") or "").strip() or "응답을 만들지 못했습니다."

    def _build_prompt(self, text, state, history):
        summary = state.get("summary", "현재 진행 중인 작업 없음")
        recent = history[-8:] if isinstance(history, list) else []
        history_text = "\n".join([f"{h.get('role')}: {h.get('content')}" for h in recent])

        return f"""
너는 PICK이라는 한국어 AI 챗봇이다.

추가 이해 규칙:
- 사용자가 새 단어를 알려주면 그 단어를 고유명사로 존중한다.
- 고유명사를 마음대로 영어 단어나 비슷한 다른 단어로 바꾸지 않는다.
- 오타 보정 결과가 있으면 그 결과를 기준으로 답한다.
- 한국어 질문에는 한국어로만 답한다.

정중하고 자연스럽게 답한다.
사용자의 작업 흐름을 기억하고 이어서 도와준다.
모르면 아는 척하지 말고 필요한 정보를 한 가지만 물어본다.
답변은 실용적으로 한다.

현재 상태:
{summary}

최근 대화:
{history_text}

사용자:
{text}

PICK:
""".strip()


class PickLLMRouter:
    def __init__(self):
        self.mode = os.environ.get("PICK_LLM_MODE", "auto").lower()
        self.local = PickLocalLLM()
        self.ollama = PickOllamaLLM()

    def generate(self, text, state=None, history=None):
        if self.mode == "local":
            return self.local.generate(text, state, history)

        if self.mode == "ollama":
            return self.ollama.generate(text, state, history)

        try:
            return self.ollama.generate(text, state, history)
        except Exception:
            return self.local.generate(text, state, history)
