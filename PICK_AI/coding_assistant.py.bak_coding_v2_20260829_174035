from __future__ import annotations

import re
from pathlib import Path

CODE_KEYWORDS = [
    "코드", "코딩", "프로그래밍", "개발", "구현", "만들어줘", "만들어 주세요",
    "에러", "오류", "버그", "디버그", "수정해", "고쳐줘", "고쳐 주세요",
    "traceback", "stack trace", "exception", "syntaxerror", "typeerror", "nameerror",
    "python", "javascript", "typescript", "java", "c++", "c#", "html", "css",
    "react", "vue", "node", "npm", "flask", "django", "fastapi", "sql", "docker",
    "github", "git", "powershell", "cmd", "batch", "bat", "bash", "curl",
    "api", "json", "yaml", "함수", "클래스", "스크립트", "파일 만들어",
    "render", "cloudflare", "cloudflared", "ollama",
]

EXTENSION_LANG = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript React", ".jsx": "JavaScript React",
    ".java": "Java", ".cpp": "C++", ".c": "C", ".cs": "C#",
    ".go": "Go", ".rs": "Rust", ".php": "PHP", ".rb": "Ruby",
    ".swift": "Swift", ".kt": "Kotlin", ".html": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".sql": "SQL", ".ps1": "PowerShell",
    ".bat": "Windows Batch", ".cmd": "Windows CMD", ".sh": "Bash",
    ".json": "JSON", ".yml": "YAML", ".yaml": "YAML",
    ".toml": "TOML", ".ini": "INI", ".env": "Environment",
}


def is_coding_query(text: str) -> bool:
    t = str(text or "").lower()
    if any(k in t for k in CODE_KEYWORDS):
        return True
    if "```" in t:
        return True
    if re.search(r"\.(py|js|ts|tsx|jsx|java|cpp|c|cs|go|rs|php|rb|swift|kt|html|css|sql|ps1|bat|cmd|sh|json|ya?ml)\b", t):
        return True
    if re.search(r"\b(pip|python|py|node|npm|git|docker|curl|ollama|cloudflared)\s+[^\n]+", t):
        return True
    return False


def coding_instruction(text: str) -> str:
    if not is_coding_query(text):
        return ""
    return (
        "[Coding mode]\n"
        "You are PICK's senior software engineer and code-repair specialist.\n"
        "A coding request must result in concrete, usable implementation rather than vague advice.\n"
        "\n"
        "WORKFLOW:\n"
        "1. Infer platform, language, filenames, architecture, error text, and target behavior from the conversation.\n"
        "2. Diagnose the likely root cause before modifying code.\n"
        "3. Produce runnable, internally consistent code.\n"
        "4. Self-check syntax, imports, names, paths, quoting, control flow, and error paths before finalizing.\n"
        "5. Give exact run/test commands when useful.\n"
        "\n"
        "IMPLEMENTATION:\n"
        "- If the user asks to create or replace a file, provide the COMPLETE file.\n"
        "- Never leave placeholders such as 'rest of code here'.\n"
        "- Preserve existing architecture when repairing code unless redesign is necessary.\n"
        "- Never invent libraries, APIs, routes, CLI flags, environment variables, functions, or filenames.\n"
        "- Keep imports, variables, routes, keys, filenames, and environment variables mutually consistent.\n"
        "- For multi-file changes, label every filename and ensure the files work together.\n"
        "- Use actual implementation, not pseudocode, unless pseudocode was requested.\n"
        "- If a reasonable safe default is possible, implement it rather than refusing because of minor missing details.\n"
        "- Never claim code was executed, compiled, deployed, or tested unless evidence shows it was.\n"
        "- Never expose secrets.\n"
        "\n"
        "DEBUGGING:\n"
        "- Identify the first/root failure and distinguish later secondary errors.\n"
        "- Explain the root cause briefly, then provide the corrected implementation.\n"
        "- Preserve user data and create backups before destructive changes.\n"
        "\n"
        "WINDOWS:\n"
        "- For BAT/CMD verify @echo off, quoting, percent expansion, delayed expansion, parentheses, pipes, redirection, CRLF, and BOM.\n"
        "- Prefer ASCII/no-BOM BAT files when Korean text is unnecessary.\n"
        "- For PowerShell verify quoting, pipeline syntax, execution-policy assumptions, and Windows paths.\n"
        "\n"
        "PYTHON:\n"
        "- Verify syntax, indentation, imports, Python-version compatibility, scope, exceptions, and encoding.\n"
        "- When practical include a py_compile or focused verification command.\n"
        "\n"
        "WEB/JAVASCRIPT:\n"
        "- Verify async/await, promises, DOM lifecycle, duplicate events, stale state, race conditions, schemas, and browser security constraints.\n"
        "\n"
        "OUTPUT:\n"
        "- Put runnable code in fenced blocks with the correct language tag.\n"
        "- Prioritize the final implementation over long explanations.\n"
        "- For repairs, show final corrected code, not only a description of changes.\n"
    )


def language_from_filename(filename: str) -> str:
    return EXTENSION_LANG.get(Path(filename or "").suffix.lower(), "Text")
