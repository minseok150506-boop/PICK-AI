import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("PICK_DATA_DIR", BASE_DIR / "data"))
STORAGE_DIR = Path(os.environ.get("PICK_STORAGE_DIR", BASE_DIR / "storage"))
UPLOAD_DIR = STORAGE_DIR / "uploads"
GENERATED_DIR = STORAGE_DIR / "generated"
DB_PATH = Path(os.environ.get("PICK_DB_PATH", DATA_DIR / "pick_service.db"))

for folder in (DATA_DIR, STORAGE_DIR, UPLOAD_DIR, GENERATED_DIR):
    folder.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get("SECRET_KEY") or os.environ.get("PICK_SECRET_KEY") or "CHANGE-ME-PICK-LOCAL"
ADMIN_USERNAME = os.environ.get("PICK_ADMIN_USERNAME", "minseok")
ADMIN_PASSWORD = os.environ.get("PICK_ADMIN_PASSWORD", "change-this-password")

OLLAMA_HOST = (
    os.environ.get("PICK_AI_BACKEND_URL")
    or os.environ.get("PICK_OLLAMA_HOST")
    or os.environ.get("OLLAMA_HOST")
    or "http://127.0.0.1:11434"
).rstrip("/")

OLLAMA_MODEL = os.environ.get("PICK_OLLAMA_MODEL") or os.environ.get("OLLAMA_MODEL") or "qwen3:8b"
OLLAMA_FALLBACK_MODELS = [
    x.strip() for x in os.environ.get(
        "PICK_OLLAMA_FALLBACK_MODELS",
        "qwen3:8b,qwen3:4b,llama3:latest"
    ).split(",") if x.strip()
]
VISION_MODEL = os.environ.get("PICK_VISION_MODEL", "llava:latest")

MAX_UPLOAD_MB = int(os.environ.get("PICK_MAX_UPLOAD_MB", "150"))
MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024

SESSION_COOKIE_SECURE = (
    os.environ.get("PICK_COOKIE_SECURE", "1" if os.environ.get("RENDER") else "0") == "1"
)
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
ALLOWED_DOC_EXT = {
    ".txt", ".md", ".json", ".csv", ".pdf", ".docx", ".xlsx",
    ".py", ".js", ".html", ".css", ".java", ".c", ".cpp", ".cs"
}


WEB_SEARCH_ENABLED = os.environ.get("PICK_WEB_SEARCH_ENABLED", "1") == "1"
RATE_LIMIT_CHAT_PER_MIN = int(os.environ.get("PICK_CHAT_PER_MIN", "20"))
RATE_LIMIT_LOGIN_PER_10MIN = int(os.environ.get("PICK_LOGIN_PER_10MIN", "12"))
TRUST_PROXY_HEADERS = os.environ.get("PICK_TRUST_PROXY_HEADERS", "1") == "1"
