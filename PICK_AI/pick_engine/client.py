from __future__ import annotations
import json
import os
import urllib.request

ENGINE_URL = os.environ.get("PICK_NATIVE_ENGINE_URL", "http://127.0.0.1:11500").rstrip("/")

def _json_request(path, payload=None, timeout=120):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(ENGINE_URL + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def health():
    try:
        return _json_request("/health", None, 5)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def generate(prompt, max_new_tokens=256, temperature=0.8, top_p=0.92):
    result = _json_request("/generate", {
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
        "temperature": temperature,
        "top_p": top_p,
    })
    if not result.get("ok"):
        raise RuntimeError(result.get("error") or "PICK Native Engine error")
    return result["text"]
