from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

OLLAMA_HOST = os.environ.get("PICK_OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("PICK_OLLAMA_MODEL", "qwen3:8b")

SYSTEM_PROMPT = """너는 PICK AI다.
한국어로 자연스럽고 똑똑하게 답한다.
사용자의 말을 최대한 이해해서 바로 답한다.
불필요한 안내문을 반복하지 않는다.
"""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/healthz")
def healthz():
    return {"ok": True, "service": "PICK AI"}

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"ok": False, "response": "메시지를 입력해 주세요."})

    prompt = f"{SYSTEM_PROMPT}\n\n사용자: {message}\nPICK AI:"

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.35,
                    "top_p": 0.9,
                    "num_predict": 1200
                }
            },
            timeout=300
        )
        response.raise_for_status()
        answer = (response.json().get("response") or "").strip()
        if not answer:
            answer = "잠시 후 다시 시도해 주세요."
        return jsonify({"ok": True, "response": answer})
    except Exception:
        return jsonify({
            "ok": False,
            "response": "AI 서버에 연결하지 못했습니다. Ollama와 Cloudflare Tunnel 상태를 확인해 주세요."
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
