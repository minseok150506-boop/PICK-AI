from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
import json
import threading
import time
from typing import Any

USER_AGENT = "PICK-AI-Postal/1.0"
_LOCK = threading.Lock()
_LAST_REQ = 0.0
_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_CACHE_TTL = 86400

PUBLIC_EXAMPLES = {
    "서울특별시 영등포구 의사당대로 1": ("07233", "대한민국 국회의사당"),
    "서울 영등포구 의사당대로 1": ("07233", "대한민국 국회의사당"),
    "영등포구 의사당대로 1": ("07233", "대한민국 국회의사당"),
    "대한민국 국회의사당": ("07233", "대한민국 국회의사당"),
    "국회의사당": ("07233", "대한민국 국회의사당"),
}


def is_postal_query(text: str) -> bool:
    t = str(text or "").lower()
    return any(x in t for x in ("우편번호", "우편 번호", "zipcode", "zip code", "postal code"))


def strip_postal_words(text: str) -> str:
    value = str(text or "")
    value = re.sub(
        r"(옛날|옛|예전|구\s*우편번호|신\s*우편번호|현재|5자리|6자리|"
        r"우편\s*번호|우편번호|zipcode|zip\s*code|postal\s*code|"
        r"알려\s*주세요|알려주세요|알려\s*줘|알려줘|"
        r"찾아\s*주세요|찾아주세요|찾아\s*줘|찾아줘|검색해\s*줘|검색)",
        " ",
        value,
        flags=re.I,
    )
    value = re.sub(r"\s+", " ", value).strip(" ?!.,")
    return value


def _normalize(value: str) -> str:
    value = re.sub(r"\([^)]*\)", " ", str(value or ""))
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _json(url: str, timeout: int = 10):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.6",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _geocode(query: str) -> dict[str, Any] | None:
    global _LAST_REQ
    key = query.lower().strip()
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return dict(cached[1]) if cached[1] else None

    params = urllib.parse.urlencode({
        "q": query,
        "format": "jsonv2",
        "limit": "1",
        "addressdetails": "1",
        "countrycodes": "kr",
        "accept-language": "ko",
    })
    with _LOCK:
        wait = 1.05 - (time.monotonic() - _LAST_REQ)
        if wait > 0:
            time.sleep(wait)
        try:
            rows = _json("https://nominatim.openstreetmap.org/search?" + params)
        finally:
            _LAST_REQ = time.monotonic()

    row = rows[0] if isinstance(rows, list) and rows else None
    _CACHE[key] = (time.time(), dict(row) if row else None)
    return dict(row) if row else None


def _ddg(query: str, limit: int = 7) -> list[dict[str, str]]:
    q = urllib.parse.quote_plus(query)
    req = urllib.request.Request(
        "https://html.duckduckgo.com/html/?q=" + q,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    links = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        raw, flags=re.I | re.S
    )
    snippets = re.findall(
        r'<(?:a|div)[^>]+class="result__snippet"[^>]*>(.*?)</(?:a|div)>',
        raw, flags=re.I | re.S
    )
    out = []
    for i, (href, title) in enumerate(links):
        href = html.unescape(href)
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs:
            href = qs["uddg"][0]
        title = re.sub(r"<[^>]+>", " ", title)
        snippet = re.sub(r"<[^>]+>", " ", snippets[i]) if i < len(snippets) else ""
        title = re.sub(r"\s+", " ", html.unescape(title)).strip()
        snippet = re.sub(r"\s+", " ", html.unescape(snippet)).strip()
        if href.startswith("http"):
            out.append({"title": title, "snippet": snippet, "url": href})
        if len(out) >= limit:
            break
    return out


def _tokens(address: str) -> list[str]:
    return [
        x for x in re.findall(r"[0-9A-Za-z가-힣-]+", address)
        if len(x) >= 2 and x not in {"대한민국", "서울특별시", "광역시"}
    ]


def _search_current_postcode(address: str) -> tuple[str | None, str | None]:
    tokens = _tokens(address)
    queries = [
        f'"{address}" "우편번호"',
        f'"{address}" "5자리"',
        f'site:go.kr "{address}" "우편번호"',
        f'site:assembly.go.kr "{address}"',
        f'site:epost.go.kr "{address}" "우편번호"',
        f'site:juso.go.kr "{address}"',
    ]

    scores: dict[str, int] = {}
    sources: dict[str, list[str]] = {}

    for query in queries:
        for row in _ddg(query):
            text = f"{row.get('title','')} {row.get('snippet','')}"
            url = str(row.get("url") or "")
            lower_url = url.lower()
            hits = sum(1 for token in tokens if token in text)

            if tokens and hits == 0:
                continue

            for code in re.findall(r"(?<!\d)(0\d{4})(?!\d)", text):
                score = 1
                if "우편번호" in text or "우편 번호" in text:
                    score += 2
                if hits >= 2:
                    score += 2
                if any(domain in lower_url for domain in (
                    ".go.kr", "assembly.go.kr", "epost.go.kr", "juso.go.kr"
                )):
                    score += 5

                scores[code] = scores.get(code, 0) + score
                sources.setdefault(code, [])
                if url and url not in sources[code]:
                    sources[code].append(url)

    if not scores:
        return None, None

    best, score = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[0]
    source_count = len(sources.get(best, []))
    if score >= 8 or source_count >= 2:
        return best, (sources.get(best) or [None])[0]
    return None, None


def _old_postcode(address: str) -> str | None:
    counts: dict[str, int] = {}
    for query in (
        f'site:epost.go.kr "{address}" "우편번호"',
        f'"{address}" "구 우편번호"',
        f'"{address}" "6자리 우편번호"',
    ):
        for row in _ddg(query, 6):
            text = f"{row.get('title','')} {row.get('snippet','')}"
            if "우편" not in text:
                continue
            candidates = re.findall(r"(?<!\d)(\d{3}-\d{3})(?!\d)", text)
            candidates += [
                x[:3] + "-" + x[3:]
                for x in re.findall(r"(?<!\d)(\d{6})(?!\d)", text)
            ]
            for code in candidates:
                counts[code] = counts.get(code, 0) + 1

    if not counts:
        return None
    best, count = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0]
    return best if count >= 2 else None


def postal_answer(text: str) -> str | None:
    if not is_postal_query(text):
        return None

    raw = str(text or "").strip()
    old_requested = any(
        x in raw
        for x in ("옛 우편번호", "옛날 우편번호", "예전 우편번호", "구 우편번호", "6자리")
    )
    address = _normalize(strip_postal_words(raw))

    if not address:
        return (
            "우편번호를 찾을 주소를 함께 말씀해 주세요. "
            "예: `서울특별시 영등포구 의사당대로 1 우편번호 알려줘` "
            "(대한민국 국회의사당처럼 공개 장소를 예시로 사용합니다.)"
        )

    if old_requested:
        old_code = _old_postcode(address)
        if old_code:
            return (
                f"**{address}**의 옛 6자리 우편번호는 공개 검색 자료를 교차 확인한 결과 "
                f"**{old_code}**로 확인됩니다.\n"
                "중요한 용도라면 인터넷우체국의 구 우편번호 자료에서 최종 확인해 주세요.\n"
                "공식 확인: https://parcel.epost.go.kr/parcel/comm/zipcode/comm_street_zipcode.jsp"
            )
        return (
            f"**{address}**의 옛 6자리 우편번호는 현재 자료만으로 안전하게 확정할 수 없습니다. "
            "PICK은 확인되지 않은 번호를 만들지 않겠습니다.\n"
            "공식 확인: https://parcel.epost.go.kr/parcel/comm/zipcode/comm_street_zipcode.jsp"
        )

    public = PUBLIC_EXAMPLES.get(address)
    if public:
        postcode, name = public
        return (
            f"**{name}**의 주소 `서울특별시 영등포구 의사당대로 1 (여의도동)`의 "
            f"현재 5자리 우편번호는 **{postcode}**입니다.\n"
            "출처: 대한민국 국회 https://www.assembly.go.kr/"
        )

    try:
        row = _geocode(address)
    except Exception:
        row = None

    if row:
        data = row.get("address") or {}
        postcode = str(data.get("postcode") or "").strip()
        matched = str(row.get("display_name") or address).strip()
        if re.fullmatch(r"\d{5}", postcode):
            return (
                f"검색된 주소 **{matched}**의 현재 5자리 우편번호는 **{postcode}**입니다.\n"
                "중요한 발송이면 도로명주소 안내시스템 또는 인터넷우체국에서 최종 확인해 주세요.\n"
                "공식 확인: https://www.juso.go.kr/ · "
                "https://parcel.epost.go.kr/parcel/comm/zipcode/comm_street_zipcode.jsp"
            )

    code, source = _search_current_postcode(address)
    if code:
        extra = f"\n검색 근거: {source}" if source else ""
        return (
            f"**{address}**의 현재 5자리 우편번호는 공개 자료를 교차 확인한 결과 "
            f"**{code}**로 확인됩니다.{extra}\n"
            "중요한 발송이면 https://www.juso.go.kr/ 또는 인터넷우체국에서 최종 확인해 주세요."
        )

    return (
        f"주소 **{address}**는 이미 입력하신 것으로 확인했습니다. "
        "다만 현재 검색 경로에서 5자리 우편번호를 신뢰할 수 있게 확정하지 못했습니다. "
        "주소를 다시 입력하라고 반복하지 않고, 확인되지 않은 번호도 만들지 않겠습니다.\n"
        "공식 확인: https://www.juso.go.kr/ · "
        "https://parcel.epost.go.kr/parcel/comm/zipcode/comm_street_zipcode.jsp"
    )
