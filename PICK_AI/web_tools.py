from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

USER_AGENT = "PICK-AI/4.0 (+local Synology assistant)"
DEFAULT_TIMEOUT = 12


def _get(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def _json(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    return json.loads(_get(url, timeout=timeout).decode("utf-8", errors="replace"))


def needs_fresh_web(text: str) -> bool:
    t = (text or "").lower()
    keywords = [
        "오늘", "지금", "현재", "최신", "최근", "실시간", "뉴스", "날씨",
        "가격", "판매", "재고", "출시", "업데이트", "버전", "일정", "시간",
        "유튜브", "youtube", "검색", "찾아줘", "찾아 줘", "알아봐", "확인해",
        "이번주", "이번 주", "내일", "어제", "이번달", "이번 달",
    ]
    return any(k in t for k in keywords)


def is_weather_query(text: str) -> bool:
    return "날씨" in (text or "") or "기온" in (text or "") or "비 와" in (text or "")


def extract_weather_location(text: str) -> str:
    cleaned = re.sub(
        r"(오늘|내일|현재|지금|날씨|기온|온도|비|와\?|와요\?|알려줘|알려 줘|어때|어떻게)",
        " ",
        text or "",
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ?!.")
    return cleaned or "서울"


def weather(location: str) -> dict[str, Any]:
    geo_q = urllib.parse.quote(location)
    geo = _json(
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={geo_q}&count=1&language=ko&format=json"
    )
    rows = geo.get("results") or []
    if not rows:
        raise RuntimeError(f"'{location}' 위치를 찾지 못했습니다.")
    p = rows[0]
    lat, lon = p["latitude"], p["longitude"]
    forecast = _json(
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&timezone=auto&forecast_days=2"
    )
    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}
    return {
        "location": ", ".join(
            x for x in [p.get("name"), p.get("admin1"), p.get("country")] if x
        ),
        "temperature_c": current.get("temperature_2m"),
        "apparent_c": current.get("apparent_temperature"),
        "precipitation_mm": current.get("precipitation"),
        "rain_mm": current.get("rain"),
        "wind_kmh": current.get("wind_speed_10m"),
        "today_high_c": (daily.get("temperature_2m_max") or [None])[0],
        "today_low_c": (daily.get("temperature_2m_min") or [None])[0],
        "precip_probability": (daily.get("precipitation_probability_max") or [None])[0],
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "retrieved_at": datetime.now().isoformat(timespec="seconds"),
    }


def duckduckgo_search(query: str, limit: int = 5) -> list[dict[str, str]]:
    q = urllib.parse.quote_plus(query)
    raw = _get(f"https://html.duckduckgo.com/html/?q={q}").decode("utf-8", errors="replace")
    # Keep parser dependency-free. DDG HTML can change; failures simply return [].
    blocks = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        raw,
        flags=re.I | re.S,
    )
    snippets = re.findall(
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>|'
        r'<div[^>]+class="result__snippet"[^>]*>(.*?)</div>',
        raw,
        flags=re.I | re.S,
    )
    results = []
    for idx, (href, title_html) in enumerate(blocks[:limit]):
        title = re.sub(r"<[^>]+>", "", title_html)
        title = html.unescape(re.sub(r"\s+", " ", title)).strip()
        href = html.unescape(href)
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs:
            href = qs["uddg"][0]
        snippet = ""
        if idx < len(snippets):
            raw_snip = snippets[idx][0] or snippets[idx][1]
            snippet = html.unescape(
                re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw_snip))
            ).strip()
        if href.startswith("http"):
            results.append({"title": title, "url": href, "snippet": snippet, "provider": "DuckDuckGo"})
    return results


def google_news_rss(query: str, limit: int = 5) -> list[dict[str, str]]:
    q = urllib.parse.quote_plus(query)
    raw = _get(
        f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    )
    root = ET.fromstring(raw)
    results = []
    for item in root.findall("./channel/item")[:limit]:
        results.append({
            "title": (item.findtext("title") or "").strip(),
            "url": (item.findtext("link") or "").strip(),
            "published": (item.findtext("pubDate") or "").strip(),
            "provider": "Google News RSS",
        })
    return results


def youtube_results(query: str, limit: int = 5) -> list[dict[str, str]]:
    # Search the public web for YouTube pages. No YouTube API key required.
    rows = duckduckgo_search(f"site:youtube.com/watch {query}", limit=limit + 3)
    out = []
    for row in rows:
        if "youtube.com/watch" in row["url"] or "youtu.be/" in row["url"]:
            out.append(row)
        if len(out) >= limit:
            break
    if not out:
        out.append({
            "title": f"YouTube에서 '{query}' 검색",
            "url": "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query),
            "snippet": "직접 YouTube 검색 결과를 엽니다.",
        })
    return out


def build_web_context(text: str) -> dict[str, Any]:
    context: dict[str, Any] = {
        "used": False,
        "kind": None,
        "query": text,
        "results": [],
        "retrieved_at": datetime.now().isoformat(timespec="seconds"),
    }
    if not needs_fresh_web(text):
        return context

    context["used"] = True
    lowered = (text or "").lower()

    try:
        if is_weather_query(text):
            loc = extract_weather_location(text)
            context["kind"] = "weather"
            context["weather"] = weather(loc)
            return context

        if "유튜브" in lowered or "youtube" in lowered:
            context["kind"] = "youtube"
            context["results"] = youtube_results(text, 5)
            return context

        if "뉴스" in lowered:
            context["kind"] = "news"
            context["results"] = google_news_rss(text, 5)
            return context

        context["kind"] = "web"
        rows = []
        rows.extend(duckduckgo_search(text, 5))
        try:
            rows.extend(wikipedia_search(text, 2))
        except Exception:
            pass
        context["results"] = dedupe_results(rows, 7)
    except Exception as exc:
        context["error"] = str(exc)
    return context


def format_context(context: dict[str, Any]) -> str:
    if not context.get("used"):
        return ""
    if context.get("kind") == "weather" and context.get("weather"):
        w = context["weather"]
        return (
            "[실시간 날씨 자료]\n"
            f"위치: {w.get('location')}\n"
            f"현재 기온: {w.get('temperature_c')}°C\n"
            f"체감: {w.get('apparent_c')}°C\n"
            f"오늘 최고/최저: {w.get('today_high_c')}°C / {w.get('today_low_c')}°C\n"
            f"강수확률: {w.get('precip_probability')}%\n"
            f"강수량: {w.get('precipitation_mm')} mm\n"
            f"풍속: {w.get('wind_kmh')} km/h\n"
            f"출처: {w.get('source_url')}\n"
            f"조회시각: {w.get('retrieved_at')}"
        )

    rows = context.get("results") or []
    if not rows:
        return "[인터넷 검색을 시도했지만 결과를 가져오지 못했습니다.]"
    lines = [f"[인터넷 검색 자료 / 종류: {context.get('kind')}]"]
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. {row.get('title','')}\n"
            f"URL: {row.get('url','')}\n"
            f"출처: {row.get('provider') or 'Web'}\n"
            f"내용: {row.get('snippet') or row.get('published') or ''}"
        )
    lines.append(f"조회시각: {context.get('retrieved_at')}")
    return "\n".join(lines)


def wikipedia_search(query: str, limit: int = 3) -> list[dict[str, str]]:
    q = urllib.parse.quote(query)
    url = (
        "https://ko.wikipedia.org/w/api.php?action=query&list=search"
        f"&srsearch={q}&format=json&utf8=1&srlimit={limit}"
    )
    data = _json(url)
    out = []
    for item in (data.get("query") or {}).get("search", []):
        title = str(item.get("title") or "")
        snippet = html.unescape(re.sub(r"<[^>]+>", "", str(item.get("snippet") or "")))
        out.append({
            "title": title,
            "url": "https://ko.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "snippet": snippet,
            "provider": "Wikipedia",
        })
    return out


def dedupe_results(rows: list[dict[str, str]], limit: int = 7) -> list[dict[str, str]]:
    out = []
    seen = set()
    for row in rows:
        url = (row.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(row)
        if len(out) >= limit:
            break
    return out
