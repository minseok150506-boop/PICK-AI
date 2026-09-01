import os

CODING_HINTS = (
    "코드", "코딩", "프로그래밍", "에러", "오류", "버그", "디버그",
    "python", "javascript", "typescript", "java", "c++", "c#", "html", "css",
    "react", "node", "flask", "django", "fastapi", "sql", "docker", "github",
    "powershell", "bash", "api", "함수", "클래스", ".py", ".js", ".cmd", ".ps1",
)

HARD_HINTS = (
    "깊게", "자세히", "정밀", "분석", "비교", "검증", "증명", "추론",
    "원인", "설계", "전략", "계획", "법률", "법적", "수학", "계산",
    "복잡", "단계별", "장단점", "논리", "연구", "보고서",
    "analyze", "compare", "reason", "prove", "research",
)

FAST_HINTS = (
    "안녕", "고마워", "뜻", "뭐야", "무슨", "간단", "요약",
    "누구야", "어디", "언제", "몇", "추천", "알려줘", "알려 주세요",
)


def choose_model(text, selected_model=None):
    if selected_model and selected_model != "auto":
        return selected_model

    t = str(text or "").strip().lower()

    if any(k in t for k in CODING_HINTS):
        return os.environ.get("PICK_CODING_MODEL", "qwen2.5-coder:7b")

    if any(k in t for k in HARD_HINTS) or len(t) >= 260:
        return os.environ.get("PICK_SMART_MODEL", "qwen3:8b")

    if any(k in t for k in FAST_HINTS) or len(t) <= 140:
        return os.environ.get("PICK_FAST_MODEL", "gemma3:4b")

    return os.environ.get("PICK_BALANCED_MODEL", "gemma3:4b")
