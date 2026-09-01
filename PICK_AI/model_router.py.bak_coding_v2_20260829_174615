from config import OLLAMA_MODEL
from pick_llm import ollama_health

CODING_HINTS = (
    "코드", "코딩", "프로그래밍", "에러", "오류", "버그", "디버그",
    "python", "javascript", "typescript", "java", "c++", "c#", "html", "css",
    "react", "node", "flask", "django", "fastapi", "sql", "docker", "github",
    "powershell", "bash", "api", "함수", "클래스", ".py", ".js", ".cmd", ".ps1",
)

def choose_model(text, selected_model=None):
    if selected_model and selected_model != "auto":
        return selected_model

    t = str(text or "").lower()
    coding = any(k in t for k in CODING_HINTS)

    try:
        available = ollama_health()
    except Exception:
        return OLLAMA_MODEL

    if coding:
        prefs = [
            "qwen2.5-coder:14b",
            "qwen2.5-coder:7b",
            "qwen3:8b",
            OLLAMA_MODEL,
            "qwen3:4b",
        ]
    else:
        prefs = [OLLAMA_MODEL, "qwen3:8b", "qwen3:4b", "llama3:latest"]

    for model in prefs:
        if model and model in available:
            return model
    return available[0] if available else OLLAMA_MODEL
