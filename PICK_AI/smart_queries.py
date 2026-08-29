from __future__ import annotations

import html
import json
import re
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "PICK-AI/1.0 (https://github.com/minseok150506-boop/PICK-AI)"
_GEO_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_GEO_LOCK = threading.Lock()
_LAST_GEO_REQUEST = 0.0
_GEO_TTL = 24 * 60 * 60


def _json(url: str, timeout: int = 10) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _text(url: str, timeout: int = 8) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _nominatim_search(query: str, countrycodes: str | None = "kr") -> dict[str, Any] | None:
    global _LAST_GEO_REQUEST
    key = f"{countrycodes or '*'}:{query.strip().lower()}"
    cached = _GEO_CACHE.get(key)
    if cached and time.time() - cached[0] < _GEO_TTL:
        return dict(cached[1]) if cached[1] else None

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": "1",
        "addressdetails": "1",
        "accept-language": "ko",
    }
    if countrycodes:
        params["countrycodes"] = countrycodes

    with _GEO_LOCK:
        wait = 1.05 - (time.monotonic() - _LAST_GEO_REQUEST)
        if wait > 0:
            time.sleep(wait)
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
        try:
            rows = _json(url, timeout=10)
        finally:
            _LAST_GEO_REQUEST = time.monotonic()

    row = rows[0] if isinstance(rows, list) and rows else None
    _GEO_CACHE[key] = (time.time(), dict(row) if row else None)
    return dict(row) if row else None


def geocode_place(query: str) -> dict[str, Any] | None:
    value = str(query or "").strip()
    if not value:
        return None
    row = _nominatim_search(value, "kr")
    if row:
        return row
    return _nominatim_search(value, None)


def is_postal_query(text: str) -> bool:
    t = str(text or "").lower()
    return any(x in t for x in ("우편번호", "우편 번호", "zipcode", "zip code", "postal code"))


def _strip_postal_words(text: str) -> str:
    value = str(text or "")
    value = re.sub(
        r"(옛날|옛|예전|구\s*우편번호|신\s*우편번호|현재|5자리|6자리|"
        r"우편\s*번호|우편번호|zipcode|zip\s*code|postal\s*code|"
        r"알려\s*주세요|알려주세요|알려\s*줘|알려줘|찾아\s*줘|찾아줘|검색)",
        " ",
        value,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", value).strip(" ?!.,")


def _ddg_results(query: str, limit: int = 6) -> list[dict[str, str]]:
    q = urllib.parse.quote_plus(query)
    try:
        raw = _text(f"https://html.duckduckgo.com/html/?q={q}", timeout=8)
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
        clean_title = re.sub(r"<[^>]+>", " ", title)
        snippet = re.sub(r"<[^>]+>", " ", snippets[i]) if i < len(snippets) else ""
        clean_title = re.sub(r"\s+", " ", html.unescape(clean_title)).strip()
        snippet = re.sub(r"\s+", " ", html.unescape(snippet)).strip()
        if href.startswith("http"):
            out.append({"title": clean_title, "snippet": snippet, "url": href})
        if len(out) >= limit:
            break
    return out


def _old_postal_candidate(address: str) -> str | None:
    queries = [
        f'site:epost.go.kr "{address}" "우편번호"',
        f'"{address}" "구 우편번호"',
        f'"{address}" "6자리 우편번호"',
    ]
    counts: dict[str, int] = {}
    for query in queries:
        for row in _ddg_results(query, 6):
            text = f"{row.get('title','')} {row.get('snippet','')}"
            if "우편" not in text and "zip" not in text.lower():
                continue
            candidates = re.findall(r"(?<!\d)(\d{3}-\d{3})(?!\d)", text)
            candidates += [x[:3] + "-" + x[3:] for x in re.findall(r"(?<!\d)(\d{6})(?!\d)", text)]
            for candidate in candidates:
                counts[candidate] = counts.get(candidate, 0) + 1
    if not counts:
        return None
    best, count = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0]
    return best if count >= 2 else None


def postal_answer(text: str) -> str | None:
    if not is_postal_query(text):
        return None
    raw = str(text or "").strip()
    old_requested = any(
        x in raw for x in ("옛 우편번호", "옛날 우편번호", "예전 우편번호", "구 우편번호", "6자리")
    )
    address = _strip_postal_words(raw)
    if not address:
        return "우편번호를 찾을 주소를 함께 말씀해 주세요. 예: `송이로 27-1 우편번호`"

    if old_requested:
        candidate = _old_postal_candidate(address)
        if candidate:
            return (
                f"`{address}`의 옛 6자리 우편번호는 검색 자료를 교차 확인한 결과 **{candidate}**로 확인됩니다.\n"
                "옛 6자리 체계는 폐지되었으므로 중요한 용도라면 인터넷우체국 구 우편번호 자료에서 한 번 더 확인해 주세요.\n"
                "공식 확인: https://parcel.epost.go.kr/parcel/comm/zipcode/comm_street_zipcode.jsp"
            )
        return (
            f"`{address}`의 옛 6자리 우편번호는 현재 검색 자료만으로 안전하게 확정할 수 없습니다. "
            "PICK은 숫자를 추측해서 답하지 않겠습니다.\n"
            "공식 확인: https://parcel.epost.go.kr/parcel/comm/zipcode/comm_street_zipcode.jsp"
        )

    try:
        row = geocode_place(address)
    except Exception as exc:
        return f"`{address}` 우편번호를 확인하는 중 오류가 발생했습니다. ({exc})"

    if not row:
        return (
            f"`{address}`와 정확히 일치하는 주소를 찾지 못했습니다. 도로명과 건물번호를 함께 입력해 주세요. "
            "예: `송이로 27-1 우편번호`"
        )

    address_data = row.get("address") or {}
    postcode = str(address_data.get("postcode") or "").strip()
    matched = str(row.get("display_name") or address).strip()
    if re.fullmatch(r"\d{5}", postcode):
        return (
            f"검색된 주소 **{matched}**의 현재 5자리 우편번호는 **{postcode}**입니다.\n"
            "중요한 발송이면 공식 주소와 한 번 더 대조해 주세요.\n"
            "공식 확인: https://www.juso.go.kr/ · "
            "https://parcel.epost.go.kr/parcel/comm/zipcode/comm_street_zipcode.jsp"
        )

    return (
        f"`{address}`의 주소는 **{matched}**로 검색됐지만 5자리 우편번호를 신뢰할 수 있게 확인하지 못했습니다. "
        "PICK은 확인되지 않은 우편번호를 만들어내지 않겠습니다.\n"
        "공식 확인: https://www.juso.go.kr/"
    )


_NAV_KEYWORDS = (
    "네비", "내비", "내비게이션", "네비게이션", "길찾기", "경로",
    "차로", "자동차로", "도보", "걸어서", "자전거", "몇 분", "몇분",
    "얼마나 걸", "도착 시간", "이동 시간",
)


def is_navigation_query(text: str) -> bool:
    t = str(text or "").lower()
    if any(x in t for x in _NAV_KEYWORDS):
        return ("까지" in t or "에서" in t or "네비" in t or "내비" in t or "길찾기" in t)
    return False


def _route_mode(text: str) -> tuple[str, str]:
    t = str(text or "").lower()
    if "도보" in t or "걸어서" in t or "걷" in t:
        return "foot", "도보"
    if "자전거" in t or "bike" in t or "cycling" in t:
        return "bike", "자전거"
    return "car", "자동차"


def _clean_place(value: str) -> str:
    value = re.sub(
        r"(현재\s*위치|내\s*위치|여기|네비게이션|내비게이션|네비|내비|길찾기|"
        r"차로|자동차로|도보로|걸어서|자전거로|몇\s*분|얼마나\s*걸려|얼마나\s*걸리|"
        r"이동\s*시간|도착\s*시간|시간|알려\s*줘|알려줘|알려주세요)",
        " ",
        str(value or ""),
        flags=re.I,
    )
    return re.sub(r"\s+", " ", value).strip(" ?!.,")


def parse_navigation_request(text: str) -> dict[str, Any] | None:
    if not is_navigation_query(text):
        return None
    raw = str(text or "").strip()
    mode, mode_label = _route_mode(raw)
    origin_text = ""
    destination = ""

    m = re.search(r"(.+?)에서\s+(.+?)까지", raw)
    if m:
        left = m.group(1).strip()
        right = m.group(2).strip()
        if not re.fullmatch(r"(현재\s*위치|내\s*위치|여기)", left):
            origin_text = _clean_place(left)
        destination = _clean_place(right)
    else:
        m = re.search(r"(?:현재\s*위치|내\s*위치|여기)(?:에서)?\s+(.+?)까지", raw)
        if m:
            destination = _clean_place(m.group(1))
        else:
            m = re.search(r"(.+?)까지(?:\s|$)", raw)
            if m:
                destination = _clean_place(m.group(1))

    if not destination and any(x in raw.lower() for x in ("네비", "내비", "길찾기")):
        destination = _clean_place(raw)

    return {
        "origin_text": origin_text,
        "destination": destination,
        "mode": mode,
        "mode_label": mode_label,
    }


def _coord(row: dict[str, Any]) -> tuple[float, float]:
    return float(row["lat"]), float(row["lon"])


def _format_duration(seconds: float) -> str:
    minutes = max(1, int(round(seconds / 60)))
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}시간 {mins}분"
    if hours:
        return f"{hours}시간"
    return f"{mins}분"


def _route_request(origin: tuple[float, float], destination: tuple[float, float], mode: str) -> dict[str, Any] | None:
    endpoint = {
        "car": "https://routing.openstreetmap.de/routed-car",
        "bike": "https://routing.openstreetmap.de/routed-bike",
        "foot": "https://routing.openstreetmap.de/routed-foot",
    }.get(mode, "https://routing.openstreetmap.de/routed-car")
    olat, olon = origin
    dlat, dlon = destination
    coords = f"{olon:.6f},{olat:.6f};{dlon:.6f},{dlat:.6f}"
    url = f"{endpoint}/route/v1/driving/{coords}?overview=false&steps=false&alternatives=false"
    data = _json(url, timeout=15)
    if not isinstance(data, dict) or data.get("code") != "Ok":
        return None
    routes = data.get("routes") or []
    return routes[0] if routes else None


def navigation_answer(text: str, payload: dict[str, Any] | None = None) -> str | None:
    parsed = parse_navigation_request(text)
    if parsed is None:
        return None
    payload = payload or {}
    destination_text = parsed["destination"]
    if not destination_text:
        return "도착지를 말씀해 주세요. 예: `현재 위치에서 서울역까지 차로 몇 분?`"

    if parsed["origin_text"]:
        try:
            origin_row = geocode_place(parsed["origin_text"])
        except Exception as exc:
            return f"출발지 `{parsed['origin_text']}`를 찾는 중 오류가 발생했습니다. ({exc})"
        if not origin_row:
            return f"출발지 `{parsed['origin_text']}`를 찾지 못했습니다."
        origin_coord = _coord(origin_row)
        origin_label = str(origin_row.get("display_name") or parsed["origin_text"]).split(",")[0]
    else:
        lat = payload.get("latitude")
        lon = payload.get("longitude")
        if lat is None or lon is None:
            return (
                "기본 출발지는 현재 위치입니다. 브라우저에서 PICK 위치 권한을 허용해 주세요. "
                "또는 `서울역에서 부산역까지 차로 몇 분?`처럼 출발지를 직접 말씀하셔도 됩니다."
            )
        try:
            origin_coord = (float(lat), float(lon))
        except Exception:
            return "현재 위치 좌표를 올바르게 확인하지 못했습니다."
        origin_label = "현재 위치"

    try:
        destination_row = geocode_place(destination_text)
    except Exception as exc:
        return f"도착지 `{destination_text}`를 찾는 중 오류가 발생했습니다. ({exc})"
    if not destination_row:
        return f"도착지 `{destination_text}`를 찾지 못했습니다. 장소명이나 주소를 조금 더 정확히 입력해 주세요."

    destination_coord = _coord(destination_row)
    destination_label = str(destination_row.get("display_name") or destination_text).split(",")[0]

    try:
        route = _route_request(origin_coord, destination_coord, parsed["mode"])
    except Exception as exc:
        return f"경로를 계산하는 중 오류가 발생했습니다. ({exc})"
    if not route:
        return f"{origin_label}에서 {destination_label}까지 경로를 찾지 못했습니다."

    distance_km = float(route.get("distance") or 0) / 1000
    duration = _format_duration(float(route.get("duration") or 0))
    return (
        f"**{origin_label} → {destination_label}**\n"
        f"- 이동수단: {parsed['mode_label']}\n"
        f"- 예상 거리: 약 **{distance_km:.1f}km**\n"
        f"- 예상 이동시간: 약 **{duration}**\n\n"
        "이 시간은 OpenStreetMap 도로망 기반 경로 예상치이며 **실시간 교통체증·사고·공사 상황은 반영하지 않습니다.** "
        "출발지를 직접 말하면 현재 위치보다 사용자가 지정한 출발지를 우선합니다.\n"
        "경로 데이터: OpenStreetMap / OSRM"
    )
