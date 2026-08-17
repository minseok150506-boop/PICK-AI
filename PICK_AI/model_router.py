from config import OLLAMA_MODEL
from pick_llm import ollama_health
def choose_model(text,selected_model=None):
    if selected_model and selected_model!="auto": return selected_model
    try: available=ollama_health()
    except Exception: return None
    t=(text or "").lower()
    prefs=["qwen2.5-coder:14b","qwen2.5-coder:7b","qwen3:8b","qwen3:4b"] if any(k in t for k in ["코드","python","javascript","java","c++"]) else [OLLAMA_MODEL,"qwen3:8b","qwen3:4b","llama3:latest"]
    for m in prefs:
        if m in available:return m
    return available[0] if available else None
