from __future__ import annotations

import re
from typing import Any, Callable

_PERSON_ENDINGS = (
    "누구야", "누구예요", "누구에요", "누구인가요", "누구인가", "누구지",
    "누구임", "누구냐", "누구인지 알려줘", "누구인지 알려주세요",
    "어떤 사람이야", "어떤 사람인가요", "어떤 사람인지 알려줘",
    "어떤 인물이야", "어떤 인물인가요",
)

_GENERIC_NAMES = {
    "", "이 사람", "그 사람", "저 사람", "이분", "그분", "저분",
    "사람", "인물", "누구",
}


def is_person_query(text: str) -> bool:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    lowered = value.lower()
    if re.search(r"\bwho\s+is\s+.{1,100}", lowered):
        return True
    if any(ending in value for ending in _PERSON_ENDINGS):
        return True
    return bool(
        re.search(
            r"^.{1,100}?(?:은|는|이|가)?\s*누구(?:야|예요|에요|인가요|인가|지|임|냐)?[?!. ]*$",
            value,
        )
    )


def extract_person_name(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    value = re.sub(r"^[Ww]ho\s+is\s+", "", value)
    value = re.sub(
        r"(?:은|는|이|가)?\s*(?:누구야|누구예요|누구에요|누구인가요|누구인가|누구지|누구임|누구냐|"
        r"누구인지\s*알려\s*줘|누구인지\s*알려\s*주세요|"
        r"어떤\s*사람이야|어떤\s*사람인가요|어떤\s*사람인지\s*알려\s*줘|"
        r"어떤\s*인물이야|어떤\s*인물인가요)\s*[?!.]*$",
        "",
        value,
        flags=re.I,
    )
    value = re.sub(r"\s*(?:에 대해|정보|프로필)\s*$", "", value)
    value = value.strip(" ?!.\"'")
    return "" if value in _GENERIC_NAMES else value[:100]


def _normalize_row(
    row: dict[str, Any],
    provider: str,
    source_type: str,
) -> dict[str, str] | None:
    url = str(row.get("url") or "").strip()
    title = str(row.get("title") or "").strip()
    if not url.startswith(("http://", "https://")):
        return None
    return {
        "title": title or url,
        "url": url,
        "snippet": str(row.get("snippet") or "").strip()[:1200],
        "provider": str(row.get("provider") or provider).strip() or provider,
        "source_type": source_type,
        "published_at": str(row.get("published_at") or "").strip(),
    }


def _dedupe(rows: list[dict[str, str]], limit: int = 18) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen_urls = set()
    seen_titles = set()
    for row in rows:
        url_key = row.get("url", "").split("#", 1)[0].rstrip("/").lower()
        title_key = re.sub(r"\s+", " ", row.get("title", "").lower()).strip()
        if not url_key or url_key in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        if title_key:
            seen_titles.add(title_key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def research_person(
    query: str,
    *,
    search_web: Callable[[str, int], list[dict[str, str]]],
    search_wikipedia: Callable[[str, int], list[dict[str, str]]],
    search_news: Callable[[str, int], list[dict[str, str]]],
    search_youtube: Callable[[str, int], list[dict[str, str]]],
) -> dict[str, Any]:
    name = extract_person_name(query)
    if not name:
        return {
            "person_name": "",
            "results": [],
            "warning": "인물 이름을 정확히 추출하지 못했습니다.",
        }

    groups: list[dict[str, str]] = []

    try:
        for row in search_wikipedia(name, 3):
            item = _normalize_row(row, "Wikipedia", "wikipedia")
            if item:
                item["provider"] = "Wikipedia"
                groups.append(item)
    except Exception:
        pass

    try:
        for row in search_web(f'site:namu.wiki "{name}"', 4):
            if "namu.wiki" not in str(row.get("url") or ""):
                continue
            item = _normalize_row(row, "나무위키", "namuwiki")
            if item:
                item["provider"] = "나무위키"
                groups.append(item)
    except Exception:
        pass

    try:
        for row in search_news(f"{name} 뉴스", 6):
            item = _normalize_row(row, str(row.get("provider") or "뉴스"), "news")
            if item:
                groups.append(item)
    except Exception:
        pass

    try:
        for row in search_youtube(name, 5):
            item = _normalize_row(row, "YouTube", "youtube")
            if item:
                item["provider"] = "YouTube"
                groups.append(item)
    except Exception:
        pass

    try:
        for row in search_web(f'"{name}"', 7):
            item = _normalize_row(row, "Web", "web")
            if item:
                groups.append(item)
    except Exception:
        pass

    try:
        for row in search_web(f'"{name}" 공식 프로필', 4):
            item = _normalize_row(row, "Web", "web")
            if item:
                groups.append(item)
    except Exception:
        pass

    preferred_order = {
        "wikipedia": 0,
        "news": 1,
        "web": 2,
        "namuwiki": 3,
        "youtube": 4,
    }
    groups.sort(key=lambda x: preferred_order.get(x.get("source_type", "web"), 9))
    results = _dedupe(groups, 18)

    counts: dict[str, int] = {}
    for row in results:
        kind = row.get("source_type", "web")
        counts[kind] = counts.get(kind, 0) + 1

    return {
        "person_name": name,
        "results": results,
        "source_counts": counts,
        "warning": "" if results else "공개 검색 결과를 충분히 가져오지 못했습니다.",
    }
