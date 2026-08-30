from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

from config import OLLAMA_HOST

class CouncilCancelled(RuntimeError):
    pass


DEFAULT_COUNCIL_MODELS = [
    ("Alibaba Qwen", "qwen3:8b"),
    ("Google Gemma", "gemma3:4b"),
    ("Meta Llama", "llama3.1:8b"),
    ("Mistral AI", "mistral:7b"),
    ("Microsoft Phi", "phi4-mini:3.8b"),
    ("DeepSeek", "deepseek-r1:8b"),
]


def _request(path: str, payload: dict[str, Any] | None = None, timeout: int = 180):
    body = None
    method = "GET"
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        method = "POST"
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        OLLAMA_HOST.rstrip("/") + path,
        data=body,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def available_models() -> list[str]:
    try:
        data = _request("/api/tags", timeout=8)
    except Exception:
        return []
    return [
        str(row.get("name") or "").strip()
        for row in data.get("models", [])
        if str(row.get("name") or "").strip()
    ]


def configured_models():
    raw = str(os.environ.get("PICK_COUNCIL_MODELS") or "").strip()
    if not raw:
        return list(DEFAULT_COUNCIL_MODELS)

    labels = {
        "qwen": "Alibaba Qwen",
        "gemma": "Google Gemma",
        "llama": "Meta Llama",
        "mistral": "Mistral AI",
        "phi": "Microsoft Phi",
        "deepseek": "DeepSeek",
    }
    out = []
    for model in [x.strip() for x in raw.split(",") if x.strip()]:
        lower = model.lower()
        company = next((v for k, v in labels.items() if k in lower), "Local model")
        out.append((company, model))
    return out


def _user_text(prompt: str) -> str:
    value = str(prompt or "")
    matches = list(re.finditer(r"\n사용자:\n", value))
    if matches:
        value = value[matches[-1].end():]
        if "\n\nPICK:" in value:
            value = value.split("\n\nPICK:", 1)[0]
    return value.strip()


def should_use_council_prompt(prompt: str) -> bool:
    enabled = str(os.environ.get("PICK_COUNCIL_ENABLED", "1")).lower().strip()
    if enabled in {"0", "false", "off", "no"}:
        return False

    value = str(prompt or "")
    if any(marker in value for marker in (
        "[Coding mode]",
        "[Translation mode]",
        "[PICK NEWS DETAIL MODE]",
        "반드시 JSON만 출력하세요",
        "JSON만 출력하세요",
    )):
        return False

    text = _user_text(value)
    lower = text.lower()
    if len(text) < 8:
        return False

    if any(x in lower for x in (
        "안녕", "고마워", "감사", "번역", "translate",
        "코드", "코딩", "오류", "에러", "버그",
        "날씨", "기온", "풍향", "풍속", "우편번호",
        "네비", "내비", "길찾기", "엑셀", "워드",
        "ppt", "프레젠테이션", "파일 만들어",
    )):
        return False

    signals = (
        "누구", "뭐야", "무엇", "왜", "어떻게", "설명", "알려",
        "정확", "사실", "비교", "차이", "원인", "추천", "의미",
        "역사", "과학", "수학", "법", "정보", "검증", "확인",
        "who", "what", "why", "how", "compare", "explain",
    )
    return "?" in text or any(x in lower for x in signals)


def _generate(model: str, prompt: str, num_predict: int, timeout: int, is_cancelled=None) -> str:
    if is_cancelled and is_cancelled():
        raise CouncilCancelled()

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "keep_alive": 0,
        "think": False,
        "options": {
            "temperature": 0.18,
            "top_p": 0.90,
            "num_ctx": 8192,
            "num_predict": num_predict,
        },
    }
    req = urllib.request.Request(
        OLLAMA_HOST.rstrip("/") + "/api/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"},
        method="POST",
    )
    parts = []
    with urllib.request.urlopen(req, timeout=timeout) as response:
        for raw in response:
            if is_cancelled and is_cancelled():
                raise CouncilCancelled()
            if not raw.strip():
                continue
            item = json.loads(raw.decode("utf-8", errors="replace"))
            chunk = str(item.get("response") or "")
            if chunk:
                parts.append(chunk)
            if item.get("error"):
                raise RuntimeError(str(item.get("error")))
            if item.get("done"):
                break

    if is_cancelled and is_cancelled():
        raise CouncilCancelled()
    return "".join(parts).strip()


def generate_consensus(prompt: str, timeout_each: int = 600, is_cancelled=None):
    if is_cancelled and is_cancelled():
        raise CouncilCancelled()

    installed = set(available_models())
    council = [(company, model) for company, model in configured_models() if model in installed]
    if len(council) < 2:
        return None

    reviewer_prompt = (
        "/no_think\n"
        "[PICK 독립 검토]\n"
        "- 제공된 실시간/검색 근거가 있으면 모델 기억보다 근거를 우선하세요.\n"
        "- 모르는 내용은 만들지 마세요.\n"
        "- 사실과 추정을 구분하세요.\n"
        "- 핵심 답과 근거만 작성하세요.\n\n"
        + str(prompt)
    )

    opinions = []
    errors = []
    for company, model in council:
        if is_cancelled and is_cancelled():
            raise CouncilCancelled()
        try:
            answer = _generate(
                model, reviewer_prompt, 360, timeout_each,
                is_cancelled=is_cancelled,
            )
            if answer:
                opinions.append({
                    "company": company,
                    "model": model,
                    "answer": answer[:8000],
                })
        except CouncilCancelled:
            raise
        except Exception as exc:
            errors.append({"model": model, "error": str(exc)[:300]})

    if is_cancelled and is_cancelled():
        raise CouncilCancelled()
    if len(opinions) < 2:
        return None

    evidence = "\n\n".join(
        f"[검토 {i} | {row['company']} | {row['model']}]\n{row['answer']}"
        for i, row in enumerate(opinions, 1)
    )

    judge_model = next(
        (model for _, model in council if model == "qwen3:8b"),
        opinions[0]["model"],
    )
    final_prompt = f"""/no_think
당신은 PICK의 최종 합의 편집기입니다.
여러 회사의 로컬 AI 검토 결과를 비교해 최종 답변 하나만 작성하세요.

독립 검토 결과:
{evidence}

규칙:
- 여러 모델이 공통으로 동의하는 핵심을 우선하세요.
- 다수결만으로 사실을 결정하지 마세요.
- 원래 질문에 인터넷/공식 근거가 제공되었다면 그 근거가 모델 의견보다 우선합니다.
- 충돌하면 근거가 더 강한 쪽을 택하고 결정하기 어려우면 불확실성을 밝히세요.
- 숫자가 다르다고 근거 없이 산술평균하지 마세요. 단위와 근거를 먼저 확인하세요.
- 의견형 질문은 공통점과 중요한 차이를 종합하세요.
- 내부 모델별 답변이나 숨겨진 추론은 사용자에게 장황하게 공개하지 마세요.
- 자연스러운 한국어 존댓말로 PICK의 최종 답변만 작성하세요.
"""
    try:
        final_answer = _generate(
            judge_model, final_prompt, 850, max(timeout_each, 600),
            is_cancelled=is_cancelled,
        )
    except CouncilCancelled:
        raise
    except Exception:
        final_answer = ""

    if is_cancelled and is_cancelled():
        raise CouncilCancelled()
    if not final_answer:
        final_answer = opinions[0]["answer"]

    return {
        "answer": final_answer.strip(),
        "contributors": [
            {"company": x["company"], "model": x["model"]}
            for x in opinions
        ],
        "errors": errors,
        "judge_model": judge_model,
    }
