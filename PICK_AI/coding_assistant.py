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
    return """[Coding mode]
Act as a senior software engineer.
- Produce runnable, internally consistent code.
- State exact filenames and where each code block belongs when relevant.
- Do not invent libraries, functions, routes, or configuration keys.
- Preserve existing project architecture unless a change is necessary.
- When fixing a bug, explain the root cause briefly and provide the corrected code.
- Prefer secure defaults and validate user input.
- For multi-file changes, clearly separate files.
- Never claim code was executed unless it actually was executed.
- Include commands needed to install/run only when they are actually required.
- Use fenced code blocks with the correct language tag.
"""


def language_from_filename(filename: str) -> str:
    return EXTENSION_LANG.get(Path(filename or "").suffix.lower(), "Text")
