from __future__ import annotations

import re
from question_understanding import QuestionAnalysis


def refine_search_query(analysis: QuestionAnalysis, history: list[dict] | None = None) -> str:
    """
    Build a concise search query while preserving named entities.
    This is for web retrieval only; the user's message is never replaced.
    """
    history = history or []
    q = analysis.normalized.strip()

    # For context-dependent followups, append a few recent technical terms.
    if analysis.refers_to_context and history:
        recent_text = " ".join(
            str(m.get("content", ""))
            for m in history[-4:]
            if m.get("role") == "user"
        )
        context_terms = re.findall(r"[A-Za-z][A-Za-z0-9_.:+#/-]{2,}|[가-힣]{2,}", recent_text)
        keep = []
        seen = set()
        for t in context_terms:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                keep.append(t)
            if len(keep) >= 5:
                break
        if keep:
            q = f"{q} {' '.join(keep)}"

    return re.sub(r"\s+", " ", q).strip()[:300]
