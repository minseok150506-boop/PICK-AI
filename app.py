from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

OLLAMA_HOST = os.environ.get("PICK_OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("PICK_OLLAMA_MODEL", "qwen3:8b")

SYSTEM_PROMPT = '''
너는 PICK AI다.
자연스럽고 똑똑하게 대답한다.
한국어를 우선 사용한다.
'''

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")

    prompt = f"{SYSTEM_PROMPT}\n\n사용자: {message}\nAI:"

    try:
        r = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=300
        )

        text = r.json().get("response", "응답 실패")

        return jsonify({
            "ok": True,
            "response": text
        })

    except Exception:
        return jsonify({
            "ok": False,
            "response": "잠시 후 다시 시도해주세요."
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
