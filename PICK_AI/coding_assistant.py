from __future__ import annotations

import re
from pathlib import Path

CODE_KEYWORDS = [
    "코드", "코딩", "프로그래밍", "에러", "오류", "버그", "디버그",
    "python", "javascript", "typescript", "java", "c++", "c#", "html", "css",
    "react", "vue", "node", "flask", "django", "fastapi", "sql", "docker",
    "github", "powershell", "bash", "api", "json", "yaml", "함수", "클래스",
]

EXTENSION_LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".jsx": "JavaScript React",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".ps1": "PowerShell",
    ".sh": "Bash",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
}


def is_coding_query(text: str) -> bool:
    t = str(text or "").lower()
    return any(k in t for k in CODE_KEYWORDS)


def coding_instruction(text: str) -> str:
    if not is_coding_query(text):
        return ""
    return (
        "[Coding mode]\n"
        "You are PICK's senior software engineer. A coding request must result in concrete, usable code rather than vague advice.\n"
        "- First identify the exact requested behavior, existing constraints, filenames, errors, and platform from the conversation.\n"
        "- Produce runnable and internally consistent code.\n"
        "- When fixing existing code, preserve the existing architecture and change only what is necessary.\n"
        "- When feasible, provide the complete corrected function or complete file instead of tiny disconnected fragments.\n"
        "- Keep imports, function names, routes, variables, indentation, paths, and configuration keys mutually consistent.\n"
        "- Never invent libraries, APIs, functions, files, routes, environment variables, or command-line options.\n"
        "- For an error report, explain the root cause briefly and then give the actual fix.\n"
        "- For Windows CMD/PowerShell, check quoting, delayed expansion, encoding/BOM, paths, and parentheses.\n"
        "- For Python, check syntax, imports, indentation, variable names, and exception paths before answering.\n"
        "- For JavaScript, check async/await flow, DOM state, duplicate events, and stale-state/race conditions.\n"
        "- For multi-file changes, label every filename and make the files work together.\n"
        "- Do not answer implementation requests with conceptual prose only; include implementation unless only explanation was requested.\n"
        "- Never claim code was executed or tested unless it actually was.\n"
        "- Prefer secure defaults and never expose secrets.\n"
        "- Use fenced code blocks with the correct language tag.\n"
    )

def language_from_filename(filename: str) -> str:
    return EXTENSION_LANG.get(Path(filename or "").suffix.lower(), "Text")
