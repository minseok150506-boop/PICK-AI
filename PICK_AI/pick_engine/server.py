from __future__ import annotations
import os
from flask import Flask, jsonify, request, Response, stream_with_context

from .inference import PickNativeEngine

app = Flask(__name__)
engine = None

def get_engine():
    global engine
    if engine is None:
        engine = PickNativeEngine()
    return engine

@app.get("/health")
def health():
    try:
        e = get_engine()
        return jsonify({
            "ok": True,
            "engine": "PICK Native Transformer",
            "device": str(e.device),
            "vocab_size": e.tokenizer.vocab_size,
            "max_seq_len": e.cfg.max_seq_len,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503

@app.post("/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt") or "")
    if not prompt:
        return jsonify({"ok": False, "error": "prompt가 없습니다."}), 400
    try:
        text = get_engine().generate(
            prompt,
            max_new_tokens=int(payload.get("max_new_tokens") or 256),
            temperature=float(payload.get("temperature") or 0.8),
            top_p=float(payload.get("top_p") or 0.92),
        )
        return jsonify({"ok": True, "text": text, "engine": "pick-native"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.post("/stream")
def stream():
    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt") or "")
    if not prompt:
        return jsonify({"ok": False, "error": "prompt가 없습니다."}), 400

    @stream_with_context
    def run():
        try:
            for chunk in get_engine().stream(
                prompt,
                max_new_tokens=int(payload.get("max_new_tokens") or 256),
                temperature=float(payload.get("temperature") or 0.8),
                top_p=float(payload.get("top_p") or 0.92),
            ):
                yield chunk
        except Exception as exc:
            yield f"\n[ENGINE_ERROR] {exc}"

    return Response(run(), mimetype="text/plain; charset=utf-8")

if __name__ == "__main__":
    host = os.environ.get("PICK_ENGINE_HOST", "0.0.0.0")
    port = int(os.environ.get("PICK_ENGINE_PORT", "11500"))
    app.run(host=host, port=port, threaded=True)
