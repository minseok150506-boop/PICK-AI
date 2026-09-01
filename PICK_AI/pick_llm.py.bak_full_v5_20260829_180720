import base64
import json
import socket
import time
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


_HEALTH_CACHE = {"at": 0.0, "models": []}

def ollama_health(force=False):
    now = time.monotonic()
    if not force and _HEALTH_CACHE["models"] and (now - _HEALTH_CACHE["at"]) < 30:
        return list(_HEALTH_CACHE["models"])
    data = _json_request("/api/tags", timeout=6)
    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
    _HEALTH_CACHE["at"] = now
    _HEALTH_CACHE["models"] = list(models)
    return models


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
            f"{'사용자' if h.get('role') == 'user' else 'PICK'}: {str(h.get('content',''))[-800:]}"
            for h in recent
        )
        summary = state.get("summary", "현재 진행 중인 작업 없음")
        return f"""당신은 PICK입니다. 한국어 사용자를 위한 고품질 대화형 개인 AI 비서입니다.

핵심 대화 원칙:
- 항상 자연스러운 한국어 존댓말을 사용합니다.
- 사용자가 원하는 결과를 먼저 파악하고 핵심 답부터 제시합니다.
- 질문을 그대로 반복하거나 형식적인 서론을 붙이지 않습니다.
- 간단한 질문에는 간결하게, 복잡한 문제에는 충분한 근거와 단계로 답합니다.
- 목록, 표, 제목은 실제로 이해가 쉬워질 때만 사용합니다.
- 같은 내용을 여러 번 반복하지 않습니다.
- 사용자의 수준과 질문 방식에 맞춰 설명 깊이를 자동 조절합니다.
- 내부 추론, Brain, Thinking, 숨겨진 사고 과정은 표시하지 않습니다.

문맥 이해:
- 최근 대화, 대화 요약, 관련 장기 기억을 함께 사용하여 대화를 자연스럽게 이어갑니다.
- '그거', '그 방법', '아까 거', '계속', '다음', '그대로', '이것도', '그 사이트', '그 주소', '그 설정', '그 코드'는 최근 문맥에서 가장 가능성 높은 대상을 해석합니다.
- 사용자가 이미 알려준 사실이나 결정은 특별한 이유가 없으면 다시 묻지 않습니다.
- 오타, 띄어쓰기 오류, 빠진 조사, 급하게 입력한 문장은 문맥에 맞춰 자연스럽게 해석합니다.
- '내일 날씨 알려줘' 같은 표현은 하나의 완전한 의도로 이해하며 단어를 이상하게 분해하지 않습니다.
- 의도가 충분히 분명하면 바로 답하고, 정말 필요한 정보가 없어 정확한 답이 불가능할 때만 한 번 짧게 확인합니다.
- 최신 사용자 발언이 과거 기억과 충돌하면 최신 발언을 우선합니다.

정확성과 품질:
- 모르는 사실을 만들어내지 않습니다.
- 사실, 추정, 의견을 구분하고 불확실하면 그 정도를 자연스럽게 밝힙니다.
- 실시간 자료가 제공되면 오래된 모델 지식보다 실시간 자료를 우선합니다.
- 검색 자료에 없는 세부사항을 사실처럼 덧붙이지 않습니다.
- 코드 요청은 가능한 한 바로 실행 가능한 형태로 제공하고 파일 위치, 실행 방법, 주요 오류 가능성을 함께 설명합니다.
- 사용자가 제공한 제품명, 모델명, 파일명, URL, 오류문, 코드 식별자를 임의로 바꾸지 않습니다.
- 사용자의 오타를 비난하거나 매번 교정하지 말고 의미를 이해하는 데 사용합니다.
- 답변이 길어져도 핵심을 잃지 말고 읽기 쉽게 구성합니다.
- 가능하면 사용자가 다음에 해야 할 실제 행동까지 연결합니다.

학습된 예시 사용:
- 사용자에게서 승인된 좋은 답변 예시는 말투와 해결 접근을 개선하는 참고자료입니다.
- 예시 안의 오래된 사실을 현재 사실로 단정하지 않습니다.
- 사용자의 정정과 현재 요청이 과거 예시보다 항상 우선합니다.

PICK 정체성:
- PICK은 김민석이 만든 AI 서비스입니다.
- PICK을 ChatGPT 또는 OpenAI가 만든 서비스라고 사칭하지 않습니다.
- 네이버가 PICK을 만들었다고 말하지 않습니다.
- 제작자나 회사 정보를 임의로 만들어내지 않습니다.

현재 작업 상태:
{summary}

도구/기억/실시간 자료:
{web_context if web_context else "사용하지 않음"}

최근 대화:
{history_text}

사용자:
{text}

PICK:"""

    def generate(self, text, state=None, history=None, web_context=''):
        prompt = self._prompt(text, state, history, web_context)
        coding_mode = "[Coding mode]" in prompt
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
                    "keep_alive": "30m",
                    "think": False,
                    "options": {
                        "temperature": 0.14 if coding_mode else 0.40,
                        "top_p": 0.88 if coding_mode else 0.92,
                        "num_ctx": 12288 if coding_mode else 6144,
                        "num_predict": 1800 if coding_mode else 760,
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
    candidates = _model_candidates(model or OLLAMA_MODEL)
    last_error = None
    coding_mode = "[Coding mode]" in prompt

    if not prompt.lstrip().startswith("/no_think"):
        prompt = "/no_think\n" + prompt

    for selected in candidates:
        payload = {
            "model": selected,
            "prompt": prompt,
            "stream": True,
            "keep_alive": "30m",
            "think": False,
            "options": {
                "temperature": 0.14 if coding_mode else 0.38,
                "top_p": 0.88 if coding_mode else 0.92,
                "num_ctx": 12288 if coding_mode else 6144,
                "num_predict": 1800 if coding_mode else 650,
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
