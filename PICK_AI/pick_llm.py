import base64
import json
import socket
import urllib.error
import urllib.request

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_FALLBACK_MODELS, VISION_MODEL


class OllamaError(RuntimeError):
    pass


def _json_request(path, payload=None, timeout=120):
    body = None
    method = "GET"
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        method = "POST"
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        OLLAMA_HOST + path,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise OllamaError(f"Ollama HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise OllamaError(f"Ollama 연결 실패: {exc}") from exc


def ollama_health():
    data = _json_request("/api/tags", timeout=8)
    return [m.get("name") for m in data.get("models", []) if m.get("name")]


def _model_candidates(preferred=None):
    result = []
    for model in [preferred or OLLAMA_MODEL, *OLLAMA_FALLBACK_MODELS]:
        if model and model not in result:
            result.append(model)
    return result


class PickLocalLLM:
    def generate(self, text, state=None, history=None):
        t = (text or "").strip()
        if not t:
            return "메시지를 입력해 주세요."
        if "안녕" in t:
            return "안녕하세요. 무엇을 도와드릴까요?"
        return (
            "현재 미니PC의 Ollama에 연결하지 못했습니다. "
            "미니PC 전원, Ollama 실행 상태, 내부 IP와 방화벽을 확인해 주세요."
        )


class PickOllamaLLM:
    def __init__(self, model=None, timeout=180):
        self.model = model or OLLAMA_MODEL
        self.timeout = timeout

    def _prompt(self, text, state=None, history=None, web_context=''):
        state = state or {}
        history = history or []
        recent = history[-12:]
        history_text = "\n".join(
            f"{'사용자' if h.get('role') == 'user' else 'PICK'}: {h.get('content','')}"
            for h in recent
        )
        summary = state.get("summary", "현재 진행 중인 작업 없음")
        return f"""당신은 PICK입니다.
한국어 사용자를 위한 개인 AI 비서입니다.

규칙:
- 항상 한국어 존댓말을 사용합니다.
- Brain, Thinking, 내부 추론 과정은 사용자에게 표시하지 않습니다.
- 모르는 사실을 지어내지 않습니다.
- PICK은 김민석이 만든 AI 서비스입니다. 네이버가 PICK을 만들었다고 말하지 않습니다.
- PICK의 제작자, 회사, 출처 같은 서비스 정체성 정보는 임의로 만들어내지 않습니다.
- 날씨나 현재 시간처럼 실시간 도구 결과가 제공되면 그 결과를 그대로 우선 사용하고 금융 등 다른 주제로 바꾸지 않습니다.
- 사용자가 최신 정보가 필요한 질문을 했는데 검색 자료가 없다면 최신 정보라고 단정하지 않습니다.
- 코드 요청에는 실행 가능한 코드와 필요한 파일 위치를 명확하게 설명합니다.
- 사용자가 알려준 고유명사는 마음대로 다른 단어로 바꾸지 않습니다.
- 답변은 실용적이고 자연스럽게 작성합니다.

현재 작업 상태:
{summary}

인터넷/실시간 자료:
{web_context if web_context else "사용하지 않음"}

인터넷 자료 사용 규칙:
- 자료가 있으면 그 자료를 우선 사용합니다.
- 자료에 URL이 있으면 답변 마지막에 '출처'로 짧게 표시합니다.
- 검색 결과만으로 확인되지 않는 사실은 단정하지 않습니다.
- 최신 정보 질문에서 검색에 실패했다면 최신 사실을 아는 척하지 않습니다.

최근 대화:
{history_text}

사용자:
{text}

PICK:"""

    def generate(self, text, state=None, history=None, web_context=''):
        prompt = self._prompt(text, state, history, web_context)
        last_error = None
        available = None
        try:
            available = set(ollama_health())
        except Exception:
            available = None

        for model in _model_candidates(self.model):
            if available is not None and model not in available:
                continue
            try:
                data = _json_request("/api/generate", {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.45,
                        "top_p": 0.9,
                        "num_predict": 1400,
                    }
                }, timeout=self.timeout)
                answer = str(data.get("response") or "").strip()
                if answer:
                    return answer
            except Exception as exc:
                last_error = exc

        if last_error:
            raise OllamaError(str(last_error))
        raise OllamaError("사용 가능한 Ollama 모델을 찾지 못했습니다.")


class PickLLMRouter:
    def __init__(self):
        self.ollama = PickOllamaLLM()
        self.local = PickLocalLLM()

    def generate(self, text, state=None, history=None, web_context=""):
        try:
            return self.ollama.generate(
                text, state=state, history=history, web_context=web_context
            )
        except Exception:
            return self.local.generate(text, state=state, history=history)


def vision_analyze(image_paths, prompt):
    images = []
    for path in image_paths:
        with open(path, "rb") as f:
            images.append(base64.b64encode(f.read()).decode("ascii"))

    data = _json_request("/api/chat", {
        "model": VISION_MODEL,
        "stream": False,
        "messages": [{
            "role": "user",
            "content": prompt,
            "images": images,
        }],
        "options": {"temperature": 0.2, "num_predict": 1000}
    }, timeout=240)

    return str((data.get("message") or {}).get("content") or "").strip()


def stream_generate(prompt, model=None, timeout=300):
    """Yield Ollama response chunks. Falls back to a complete error message."""
    candidates = _model_candidates(model or OLLAMA_MODEL)
    last_error = None

    try:
        available = set(ollama_health())
    except Exception:
        available = None

    for selected in candidates:
        if available is not None and selected not in available:
            continue
        payload = {
            "model": selected,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.45,
                "top_p": 0.9,
                "num_predict": 1600,
            },
        }
        req = urllib.request.Request(
            OLLAMA_HOST + "/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                for raw in response:
                    if not raw.strip():
                        continue
                    item = json.loads(raw.decode("utf-8", errors="replace"))
                    chunk = str(item.get("response") or "")
                    if chunk:
                        yield {"type": "token", "text": chunk, "model": selected}
                    if item.get("done"):
                        yield {"type": "done", "model": selected}
                        return
        except Exception as exc:
            last_error = exc
            continue

    yield {
        "type": "error",
        "text": (
            "AI 응답을 생성하지 못했습니다. PICK_AI_BACKEND_URL, 모델, "
            f"AI 백엔드 연결 상태를 확인해 주세요. ({last_error})"
        ),
    }


def build_prompt(text, state=None, history=None, web_context=""):
    return PickOllamaLLM()._prompt(text, state, history, web_context)
