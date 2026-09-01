import os
import base64
import json
import re
import sqlite3
from datetime import timedelta
from pathlib import Path

from flask import (
    Response, stream_with_context,
    Flask, jsonify, redirect, render_template, request,
    send_from_directory, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

from analyzers import analyze_document_upload, analyze_image_upload, analyze_video_upload, translate_image_upload
from config import (
    DATA_DIR, STORAGE_DIR,
    WEB_SEARCH_ENABLED, RATE_LIMIT_CHAT_PER_MIN, RATE_LIMIT_LOGIN_PER_10MIN,
    ADMIN_PASSWORD, ADMIN_USERNAME, GENERATED_DIR, MAX_CONTENT_LENGTH,
    OLLAMA_HOST, OLLAMA_MODEL, SECRET_KEY, SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE, SESSION_COOKIE_SECURE
)
from database import connect, init_db, log, now, database_status
from pick_llm import PickLLMRouter, ollama_health, stream_generate, build_prompt
from security import client_key, csrf_token, limiter, validate_csrf
from web_tools import build_web_context, format_context
from web_search_engine import search as web_search, format_for_llm as format_web_search, weather_coords
from memory_store import add_memory, delete_memory, format_memory_context, list_memories
from memory_engine import (
    add_memory as add_memory_v2,
    delete_memory as delete_memory_v2,
    export_all as export_memory_all,
    format_memory_context as format_memory_context_v2,
    get_settings as get_memory_settings,
    list_memories as list_memories_v2,
    memory_stats,
    maybe_auto_store,
    pin_memory,
    update_settings as update_memory_settings,
)
from conversation_memory import refresh_summary_if_needed, get_conversation_summary
from account_profile import get_profile, update_profile, format_profile_context
from account_isolation import assert_chat_owner, assert_message_owner, assert_attachment_owner, private_upload_dir, user_counts
from audit import write_audit
from model_router import choose_model
from language_support import SUPPORTED_LANGUAGES, language_instruction
from coding_assistant import coding_instruction, is_coding_query
from learning_store import add_feedback, approve_feedback, export_jsonl, list_feedback, training_stats, format_training_examples
from semantic_learning import rebuild_user_index, retrieve as retrieve_semantic_memory
from question_understanding import analyze_question, build_understanding_instruction
from search_query_refiner import refine_search_query
from orchestrator import orchestrate
from answer_validator import validate_answer
from seasonal_modes import list_modes as list_seasonal_modes, resolve_mode
from accurate_time import refresh_offset, status as accurate_time_status, utc_now, validate_timezone, now_in_timezone
from country_resolver import resolve_country
from google_auth import configure_google, google_enabled, oauth
from inference_guard import guard, InferenceBusy, CircuitOpen
from context_safety import wrap_untrusted_context
from smart_queries import navigation_answer
from postal_upgrade import postal_answer
from background_jobs import (
    JobCancelled, ensure_job_table,
    enqueue_job as enqueue_background_job,
    get_job_for_user, list_chat_jobs,
    cancel_job as cancel_background_job,
    start_worker as start_background_worker,
)
from people_research import is_person_query
from translation_support import translation_instruction
from office_generator import detect_office_kind, create_office_file
from admin_roles import (
    is_admin as role_is_admin,
    is_owner as role_is_owner,
    admin_label as role_admin_label,
    list_users_for_admin, promote_admin, demote_admin,
)
import migrations

from native_ai_provider import native_available, generate_native, choose_provider

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = SECRET_KEY
app.config["JSON_AS_ASCII"] = False
GOOGLE_LOGIN_ENABLED = configure_google(app)
app.config.update(
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
    SESSION_COOKIE_HTTPONLY=SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
    PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    SESSION_REFRESH_EACH_REQUEST=True,
)

llm = PickLLMRouter()




@app.get("/api/native-engine/status")
def api_native_engine_status():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    try:
        from pick_engine.client import health
        result = health()
        return jsonify({
            "ok": True,
            "provider_mode": choose_provider(),
            "native_engine": result,
        })
    except Exception as exc:
        return jsonify({
            "ok": True,
            "provider_mode": choose_provider(),
            "native_engine": {"ok": False, "error": str(exc)},
        })


@app.post("/api/native-engine/test")
def api_native_engine_test():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt") or "안녕하세요").strip()
    try:
        text = generate_native(prompt)
        return jsonify({"ok": True, "text": text, "provider": "pick-native"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503

@app.context_processor
def inject_security_context():
    return {"csrf_token": csrf_token}


@app.before_request
def pick_security_before_request():
    # Login/register POSTs also carry the hidden token.
    validate_csrf()


@app.after_request
def pick_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), geolocation=(self), payment=(), usb=()"
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "img-src 'self' data: blob: https:; "
        "media-src 'self' blob: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https:; "
        "font-src 'self' data:; "
        "frame-ancestors 'self'"
    )
    return response

def has_korean(value):
    return bool(re.search(r"[가-힣]", str(value or "")))


def valid_username(value):
    return re.fullmatch(r"[A-Za-z0-9_-]{2,32}", value or "") is not None


def valid_password(value):
    return re.fullmatch(r"[A-Za-z0-9!@#$%^&*()_\-+=.?]{4,64}", value or "") is not None


def logged_in():
    return session.get("user_id") is not None


def require_login_json():
    if not logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    return None


def login_required_view():
    if not logged_in():
        return redirect(url_for("login"))
    return None


def current_user_is_admin():
    return role_is_admin(session.get("user_id"))


def current_user_is_owner():
    return role_is_owner(session.get("user_id"))


def current_admin_label():
    return role_admin_label(session.get("user_id"))


def user_owns_chat(chat_id, user_id):
    conn = connect()
    row = conn.execute(
        "SELECT id FROM chats WHERE id=? AND user_id=?",
        (chat_id, user_id)
    ).fetchone()
    conn.close()
    return row is not None




def get_preferred_language(user_id):
    conn = connect()
    row = conn.execute("SELECT preferred_language FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return (row["preferred_language"] if row and row["preferred_language"] else "auto")


def build_system_extensions(user_id, text):
    lang = language_instruction(get_preferred_language(user_id), text)
    code = coding_instruction(text)
    translation = translation_instruction(text)
    return "\n\n".join(x for x in [lang, code, translation] if x)

def direct_realtime_or_identity_answer(text, payload=None):
    raw = str(text or "").strip()
    lowered = raw.lower()
    payload = payload or {}

    identity_phrases = (
        "누가 만들", "누가 제작", "누가 개발", "만든 사람", "제작자", "개발자",
        "어디서 만들", "어느 회사", "네이버에서 만들", "네이버가 만들"
    )
    if ("pick" in lowered or "픽" in raw) and any(p in raw for p in identity_phrases):
        return "PICK은 김민석이 만든 AI 서비스입니다. 네이버에서 만든 서비스가 아닙니다.", "identity"

    postal = postal_answer(raw)
    if postal is not None:
        return postal, "postal"

    navigation = navigation_answer(raw, payload)
    if navigation is not None:
        return navigation, "navigation"

    office_kind = detect_office_kind(raw)
    if office_kind:
        try:
            created = create_office_file(raw, office_kind)
            return (
                f"{created['label']} 파일을 만들었습니다.\n"
                f"[파일 다운로드]({created['url']})",
                "file",
            )
        except Exception as exc:
            return f"파일을 만드는 중 오류가 발생했습니다. ({exc})", "file"

    if any(word in raw for word in ("날씨", "기온", "온도", "바람", "풍향", "풍양", "풍량", "풍속")):
        try:
            latitude = payload.get("latitude")
            longitude = payload.get("longitude")
            location_words = re.sub(
                r"(오늘|내일|모레|이번\s*주|주간|현재\s*위치|내\s*위치|여기|현재|지금|실시간|날씨|기온|온도|예보|바람|풍향|풍양|풍량|풍속|"
                r"알려\s*주세요|알려주세요|알려\s*줘|알려줘|어때요|어때)",
                " ", raw
            )
            location_words = re.sub(r"[?!.~,]+", " ", location_words)
            location_words = re.sub(r"\s+", " ", location_words).strip()

            # Explicitly named places have priority over browser GPS.
            if location_words:
                result = web_search(raw, mode="always")
                w = result.get("weather") if isinstance(result, dict) else None
                if not w:
                    err = result.get("error") if isinstance(result, dict) else None
                    return "날씨 정보를 가져오지 못했습니다." + ((" (" + str(err) + ")") if err else ""), "weather"
                location_note = w.get("location") or location_words
            elif latitude is not None and longitude is not None:
                w = weather_coords(latitude, longitude)
                location_note = "현재 위치"
            else:
                if payload.get("gps_error"):
                    return ("현재 위치를 확인하지 못했습니다. 위치 권한을 허용하거나 지역명을 말씀해 주세요.", "weather")
                return ("현재 위치 정보가 필요합니다. 위치 권한을 허용하거나 지역명을 함께 말씀해 주세요.", "weather")

            dates = w.get("daily_dates") or []
            highs = w.get("daily_high_c") or []
            lows = w.get("daily_low_c") or []
            rains = w.get("daily_precip_probability") or []
            codes = w.get("daily_weather_code") or []

            def at(values, index, fallback=None):
                return values[index] if len(values) > index else fallback

            def weather_name(code):
                try:
                    code = int(code)
                except Exception:
                    return ""
                if code == 0: return "맑음"
                if code in (1, 2, 3): return "구름"
                if code in (45, 48): return "안개"
                if code in (51, 53, 55, 56, 57): return "이슬비"
                if code in (61, 63, 65, 66, 67): return "비"
                if code in (71, 73, 75, 77): return "눈"
                if code in (80, 81, 82): return "소나기"
                if code in (85, 86): return "눈 소나기"
                if code in (95, 96, 99): return "뇌우"
                return ""

            if "이번 주" in raw or "이번주" in raw or "주간" in raw:
                lines = [f"{location_note} 기준 이번 주 날씨입니다."]
                for i in range(min(7, len(dates), len(highs), len(lows))):
                    condition = weather_name(at(codes, i))
                    condition_text = f", {condition}" if condition else ""
                    lines.append(
                        f"- {at(dates, i)}: 최고 {at(highs, i)}°C / 최저 {at(lows, i)}°C, "
                        f"강수확률 {at(rains, i, '-')}%{condition_text}"
                    )
                lines.append("출처: Open-Meteo")
                return "\n".join(lines), "weather"

            day_offset = 2 if "모레" in raw else (1 if "내일" in raw else 0)
            day_label = "모레" if day_offset == 2 else ("내일" if day_offset == 1 else "오늘")
            high = at(highs, day_offset, w.get("today_high_c"))
            low = at(lows, day_offset, w.get("today_low_c"))
            rain = at(rains, day_offset, w.get("precip_probability"))
            forecast_date = at(dates, day_offset)
            condition = weather_name(at(codes, day_offset))
            condition_text = f" 날씨는 {condition}이고," if condition else ""

            if day_offset == 0:
                answer = (
                    f"{location_note} 기준 오늘 날씨입니다.\n"
                    f"현재 {w.get('temperature_c')}°C, 체감 {w.get('apparent_c')}°C입니다.\n"
                    f"오늘은{condition_text} 최고 {high}°C / 최저 {low}°C, 강수확률 {rain}%입니다.\n"
                    f"현재 강수량 {w.get('precipitation_mm')}mm, 풍속 {w.get('wind_kmh')}km/h, "
                    f"풍향 {w.get('wind_direction_name') or '-'}"
                    + (f" ({w.get('wind_direction_deg')}°)" if w.get('wind_direction_deg') is not None else "")
                    + "입니다.\n"
                    "출처: Open-Meteo"
                )
            else:
                date_note = f" ({forecast_date})" if forecast_date else ""
                answer = (
                    f"{location_note} 기준 {day_label}{date_note} 날씨입니다.\n"
                    f"{day_label}은{condition_text} 최고 {high}°C / 최저 {low}°C, 강수확률 {rain}%입니다.\n"
                    "출처: Open-Meteo"
                )
            return answer, "weather"
        except Exception as exc:
            return "날씨 정보를 가져오지 못했습니다. (" + str(exc) + ")", "weather"

    time_phrases = (
        "몇 시", "몇시", "현재 시간", "지금 시간", "시간 알려", "오늘 날짜", "오늘 며칠",
        "몇 일이야", "몇일이야", "무슨 요일", "오늘 요일", "지금 몇 월", "지금 몇월"
    )
    if any(p in raw for p in time_phrases):
        tz_name = validate_timezone(payload.get("timezone"), "Asia/Seoul")
        current = now_in_timezone(tz_name)
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        return (
            f"현재 {tz_name} 기준 {current.year}년 {current.month}월 {current.day}일 "
            f"{weekdays[current.weekday()]} {current.hour:02d}:{current.minute:02d}:{current.second:02d}입니다.",
            "time",
        )
    return None

def get_user_settings(user_id):
    conn = connect()
    row = conn.execute(
        "SELECT selected_model,web_mode,compact_mode,seasonal_override,updated_at FROM user_settings WHERE user_id=?",
        (user_id,)
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO user_settings(user_id,selected_model,web_mode,compact_mode,seasonal_override,updated_at) VALUES(?,?,?,?,?,?)",
            (user_id, "auto", "auto", 0, "auto", now())
        )
        conn.commit()
        row = conn.execute(
            "SELECT selected_model,web_mode,compact_mode,seasonal_override,updated_at FROM user_settings WHERE user_id=?",
            (user_id,)
        ).fetchone()
    conn.close()
    return dict(row)


def resolve_selected_model(user_id):
    settings = get_user_settings(user_id)
    selected = settings.get("selected_model") or "auto"
    return None if selected == "auto" else selected

def get_chats(user_id):
    conn = connect()
    rows = conn.execute(
        """SELECT id,user_id,title,created_at,updated_at
           FROM chats WHERE user_id=?
           ORDER BY datetime(updated_at) DESC, id DESC""",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


_SOURCE_MARKER_RE = re.compile(
    r"\n*\[\[PICK_SOURCES_B64:([A-Za-z0-9_-]+)\]\]\s*$"
)


def _clean_source_rows(rows):
    out = []
    seen = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url") or row.get("source_url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        key = url.split("#", 1)[0].rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "title": str(row.get("title") or row.get("location") or url).strip()[:300],
            "url": url[:2000],
            "provider": str(row.get("provider") or "PICK Search").strip()[:100],
            "source_type": str(row.get("source_type") or "web").strip()[:40],
            "published_at": str(row.get("published_at") or "").strip()[:100],
        })
        if len(out) >= 18:
            break
    return out


def _sources_from_web_result(result):
    if not isinstance(result, dict) or not result.get("used"):
        return []
    if result.get("kind") == "weather" and isinstance(result.get("weather"), dict):
        weather = result["weather"]
        return _clean_source_rows([{
            "title": "날씨 데이터",
            "url": weather.get("source_url"),
            "provider": weather.get("provider") or "Open-Meteo",
            "source_type": "weather",
        }])
    return _clean_source_rows(result.get("results") or [])


def _attach_source_marker(answer, sources):
    clean = _clean_source_rows(sources)
    if not answer or not clean:
        return answer
    raw = json.dumps(clean, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return str(answer).rstrip() + f"\n\n[[PICK_SOURCES_B64:{encoded}]]"


def _strip_source_marker(content):
    value = str(content or "")
    match = _SOURCE_MARKER_RE.search(value)
    if not match:
        return value, []
    encoded = match.group(1)
    try:
        encoded += "=" * (-len(encoded) % 4)
        rows = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8"))
        sources = _clean_source_rows(rows if isinstance(rows, list) else [])
    except Exception:
        sources = []
    return value[:match.start()].rstrip(), sources


def get_messages(chat_id):
    conn = connect()
    rows = conn.execute(
        "SELECT id,chat_id,role,content,created_at FROM chat_messages WHERE chat_id=? ORDER BY id",
        (chat_id,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        if item["role"] == "bot":
            item["role"] = "assistant"
        if item["role"] == "assistant":
            clean_content, source_rows = _strip_source_marker(item.get("content"))
            item["content"] = clean_content
            if source_rows:
                item["sources"] = source_rows
        result.append(item)
    return result


def create_chat(user_id):
    timestamp = now()
    conn = connect()
    cur = conn.execute(
        "INSERT INTO chats(user_id,title,created_at,updated_at) VALUES(?,?,?,?)",
        (user_id, "새 채팅", timestamp, timestamp)
    )
    chat_id = cur.lastrowid
    conn.commit()
    conn.close()
    return chat_id


def update_chat_title(chat_id):
    conn = connect()
    row = conn.execute(
        "SELECT content FROM chat_messages WHERE chat_id=? AND role='user' ORDER BY id LIMIT 1",
        (chat_id,)
    ).fetchone()
    if row:
        title = re.sub(r"\s+", " ", row["content"]).strip()[:36] or "새 채팅"
        conn.execute(
            "UPDATE chats SET title=?,updated_at=? WHERE id=?",
            (title, now(), chat_id)
        )
        conn.commit()
    conn.close()


def process_background_chat_job(job, update_partial, is_cancelled):
    uid=int(job["user_id"]); chat_id=int(job["chat_id"]); payload=json.loads(job.get("request_json") or "{}")
    text=str(payload.get("message") or "").strip()
    if not text: raise RuntimeError("저장된 질문이 비어 있습니다.")
    update_partial("답변을 준비하고 있습니다…",meta={"phase":"preparing"})
    direct=direct_realtime_or_identity_answer(text,payload)
    if direct is not None:
        if is_cancelled(): raise JobCancelled()
        answer,kind=direct
        return {"answer":answer,"stored_answer":answer,"sources":[],"model":"PICK-direct",
                "meta":{"route":{"primary":kind},"web_used":kind in {"weather","news"},"web_kind":kind if kind in {"weather","news"} else None}}
    history=get_messages(chat_id); recent=[{"role":m["role"],"content":m["content"]} for m in history[:-1][-16:]]
    orch=orchestrate(text,recent); qa=analyze_question(text,recent); normalized=orch.rewritten_question or qa.normalized or text; route=orch.route
    if orch.clarification:
        a=orch.clarification
        return {"answer":a,"stored_answer":a,"sources":[],"model":"clarification","meta":{"route":route,"clarification":True,"web_used":False,"web_kind":None}}
    try: conv_summary=get_conversation_summary(uid,chat_id)
    except Exception: conv_summary=""
    settings=get_user_settings(uid); web_mode=settings.get("web_mode","auto"); web_context={}; web_text=""
    if WEB_SEARCH_ENABLED and web_mode!="off" and (route.get("use_web") or web_mode=="always"):
        update_partial("인터넷 자료와 출처를 확인하고 있습니다…",meta={"phase":"web","route":route})
        try:
            q=text if is_person_query(text) else refine_search_query(qa,recent); web_context=web_search(q,mode="always"); web_text=format_web_search(web_context)
        except Exception as e: log("WARNING",f"background web search: {e}")
    if is_cancelled(): raise JobCancelled()
    memory_text=format_memory_context_v2(uid,normalized); learning_text=format_training_examples(uid,normalized,limit=3); profile_text=format_profile_context(uid)
    safe_web=wrap_untrusted_context("인터넷 검색 자료",web_text) if web_text else ""; combined="\n\n".join(x for x in [profile_text,memory_text,learning_text,safe_web] if x)
    ext=build_system_extensions(uid,normalized)
    seasonal=resolve_mode(uid,user_timezone=(payload.get("timezone") or "Asia/Seoul"),country=(str(payload.get("country") or "").upper() or None),override=settings.get("seasonal_override","auto"))
    context="\n\n".join(x for x in [orch.understanding_instruction,("[Conversation summary]\n"+conv_summary) if conv_summary else "",seasonal.system_instruction if seasonal.active else "",ext,combined] if x)
    lim=18000 if isinstance(web_context,dict) and web_context.get("kind") in {"news","person"} else 10000
    if len(context)>lim: context=context[-lim:]
    prompt=build_prompt(normalized,state={"summary":f"현재 채팅 ID {chat_id}"},history=recent,web_context=context)
    sources=_sources_from_web_result(web_context); selected=choose_model(normalized,resolve_selected_model(uid))
    meta={"route":route,"seasonal_mode":seasonal.to_dict(),"web_used":bool(web_context.get("used")) if isinstance(web_context,dict) else False,"web_kind":web_context.get("kind") if isinstance(web_context,dict) else None,"phase":"generating"}
    update_partial("답변을 생성하고 있습니다…",sources=sources,model=selected,meta=meta)
    full=[]; had_error=False; last_model=selected; n=0
    try:
        with guard.slot():
            for item in stream_generate(prompt,model=selected,is_cancelled=is_cancelled):
                if is_cancelled(): raise JobCancelled()
                if item.get("type")=="token":
                    chunk=str(item.get("text") or "")
                    if chunk:
                        full.append(chunk); n+=1; last_model=str(item.get("model") or last_model)
                        if n%4==0: update_partial("".join(full),sources=sources,model=last_model,meta=meta)
                elif item.get("type")=="error":
                    had_error=True
                    if not full: raise RuntimeError(str(item.get("text") or "AI 생성 오류"))
            guard.failure() if had_error else guard.success()
    except (InferenceBusy,CircuitOpen) as e: raise RuntimeError(str(e)) from e
    if is_cancelled(): raise JobCancelled()
    answer="".join(full).strip()
    if not answer: raise RuntimeError("PICK이 빈 답변을 생성했습니다.")
    val=validate_answer(answer,web_used=bool(web_context.get("used")) if isinstance(web_context,dict) else False,coding=bool(route.get("use_coding"))); answer=val.cleaned.strip()
    if not answer: raise RuntimeError("답변 검증 후 내용이 비어 있습니다.")
    stored=_attach_source_marker(answer,sources); update_partial(answer,sources=sources,model=last_model,meta={**meta,"phase":"finishing"})
    return {"answer":answer,"stored_answer":stored,"sources":sources,"model":last_model,"meta":meta}

def after_background_chat_job(job,result,message_id):
    try: refresh_summary_if_needed(int(job["user_id"]),int(job["chat_id"]),get_messages(int(job["chat_id"])),summarizer=None)
    except Exception as e: log("WARNING",f"background summary refresh: {e}")

init_db(); ensure_job_table(); start_background_worker(process_background_chat_job,after_complete=after_background_chat_job)


@app.errorhandler(403)
def forbidden(error):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": getattr(error, "description", "요청이 차단되었습니다.")}), 403
    return str(getattr(error, "description", "요청이 차단되었습니다.")), 403


@app.errorhandler(429)
def too_many_requests(_):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."}), 429
    return "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.", 429


@app.errorhandler(413)
def too_large(_):
    return jsonify({"ok": False, "error": "업로드 파일이 너무 큽니다."}), 413



@app.get("/api/render/status")
def api_render_status():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    return jsonify({
        "ok": True,
        "render": bool(os.environ.get("RENDER")),
        "data_dir": str(DATA_DIR),
        "storage_dir": str(STORAGE_DIR),
        "database": database_status(deep=True),
        "ai_backend_configured": bool(os.environ.get("PICK_AI_BACKEND_URL") or os.environ.get("PICK_OLLAMA_HOST") or os.environ.get("OLLAMA_HOST")),
        "google_login_configured": bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")),
    })

@app.get("/api/database/status")
def api_database_status():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    return jsonify({"ok": True, "database": database_status(deep=True)})


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "PICK AI", "mode": "synology-minipc"})


@app.get("/api/system/status")
def system_status():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    try:
        models = ollama_health()
        ollama = True
        error = None
    except Exception as exc:
        models = []
        ollama = False
        error = str(exc)
    return jsonify({
        "ok": True,
        "ollama": ollama,
        "ollama_host": OLLAMA_HOST,
        "preferred_model": OLLAMA_MODEL,
        "models": models,
        "error": error,
    })


@app.route("/")
def index():
    guard = login_required_view()
    if guard:
        return guard
    return render_template(
        "app.html",
        username=session.get("username", ""),
        is_admin=current_user_is_admin(),
        admin_label=current_admin_label()
    )


@app.get("/api/bootstrap")
def api_bootstrap():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    return jsonify({
        "ok": True,
        "username": session["username"],
        "chats": get_chats(session["user_id"]),
        "settings": get_user_settings(session["user_id"]),
    })







@app.get("/api/search/web")
def api_search_web():
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    query = str(request.args.get("q") or "").strip()
    if not query:
        return jsonify({"ok": False, "error": "검색어를 입력해 주세요."}), 400

    mode = str(request.args.get("mode") or "always").strip().lower()
    if mode not in {"auto", "always", "off"}:
        mode = "always"

    try:
        result = web_search(query, mode=mode)
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": f"인터넷 검색 중 오류가 발생했습니다: {exc}"
        }), 502

@app.get("/api/inference/status")
def api_inference_status():
    auth_err=require_login_json()
    if auth_err:return auth_err
    return jsonify({"ok":True,"queue":guard.status()})

@app.get("/api/admin/overview")
def api_admin_overview():
    auth_err=require_login_json()
    if auth_err:return auth_err
    if not current_user_is_admin():
        return jsonify({"ok":False,"error":"관리자만 접근할 수 있습니다."}),403
    conn=connect()
    counts={
      "users":conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
      "chats":conn.execute("SELECT COUNT(*) c FROM chats").fetchone()["c"],
      "messages":conn.execute("SELECT COUNT(*) c FROM chat_messages").fetchone()["c"],
      "memories":conn.execute("SELECT COUNT(*) c FROM memories").fetchone()["c"],
      "attachments":conn.execute("SELECT COUNT(*) c FROM attachments").fetchone()["c"],
      "audit_today":conn.execute("SELECT COUNT(*) c FROM audit_events WHERE date(created_at)=date('now','localtime')").fetchone()["c"],
    }
    conn.close()
    return jsonify({"ok":True,"counts":counts,"inference":guard.status(),"database":database_status(deep=False),"schema_version":migrations.LATEST_SCHEMA})



@app.get("/api/account/profile-memory")
def api_account_profile_memory_get():
    auth_err=require_login_json()
    if auth_err:return auth_err
    uid=session["user_id"]
    return jsonify({"ok":True,"profile":get_profile(uid),"counts":user_counts(uid)})

@app.post("/api/account/profile-memory")
def api_account_profile_memory_save():
    auth_err=require_login_json()
    if auth_err:return auth_err
    uid=session["user_id"]
    return jsonify({"ok":True,"profile":update_profile(uid,request.get_json(silent=True) or {})})

@app.get("/api/memory/v2")
def api_memory_v2_list():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    return jsonify({
        "ok": True,
        "memories": list_memories_v2(uid, 500),
        "settings": get_memory_settings(uid),
        "stats": memory_stats(uid),
    })


@app.post("/api/memory/v2")
def api_memory_v2_add():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    payload = request.get_json(silent=True) or {}
    try:
        mid = add_memory_v2(
            user_id=uid,
            content=str(payload.get("content") or ""),
            kind=str(payload.get("kind") or "fact"),
            title=str(payload.get("title") or ""),
            importance=int(payload.get("importance") or 3),
            confidence=float(payload.get("confidence") or 1.0),
            pinned=bool(payload.get("pinned")),
            source_chat_id=payload.get("source_chat_id"),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({
        "ok": True,
        "memory_id": mid,
        "memories": list_memories_v2(uid, 500),
        "stats": memory_stats(uid),
    })


@app.delete("/api/memory/v2/<int:memory_id>")
def api_memory_v2_delete(memory_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    if not delete_memory_v2(uid, memory_id):
        return jsonify({"ok": False, "error": "기억을 찾을 수 없습니다."}), 404
    return jsonify({
        "ok": True,
        "memories": list_memories_v2(uid, 500),
        "stats": memory_stats(uid),
    })


@app.post("/api/memory/v2/<int:memory_id>/pin")
def api_memory_v2_pin(memory_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    payload = request.get_json(silent=True) or {}
    if not pin_memory(uid, memory_id, bool(payload.get("pinned"))):
        return jsonify({"ok": False, "error": "기억을 찾을 수 없습니다."}), 404
    return jsonify({
        "ok": True,
        "memories": list_memories_v2(uid, 500),
    })


@app.get("/api/memory/v2/settings")
def api_memory_v2_settings_get():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    return jsonify({
        "ok": True,
        "settings": get_memory_settings(session["user_id"]),
    })


@app.post("/api/memory/v2/settings")
def api_memory_v2_settings_save():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    settings = update_memory_settings(
        session["user_id"],
        request.get_json(silent=True) or {}
    )
    return jsonify({"ok": True, "settings": settings})


@app.get("/api/memory/v2/export")
def api_memory_v2_export():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    data = export_memory_all(session["user_id"])
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": 'attachment; filename="pick_memory_export.json"'}
    )

@app.get("/api/memories")
def api_memories():
    auth_err=require_login_json()
    if auth_err:return auth_err
    return jsonify({"ok":True,"memories":list_memories(session["user_id"])})

@app.post("/api/memories")
def api_memory_add():
    auth_err=require_login_json()
    if auth_err:return auth_err
    payload=request.get_json(silent=True) or {}
    content=str(payload.get("content") or "").strip()
    if not content:return jsonify({"ok":False,"error":"기억할 내용을 입력해 주세요."}),400
    mid=add_memory(session["user_id"],content,payload.get("source_chat_id"),payload.get("importance",3))
    write_audit("memory.add",user_id=session["user_id"],username=session.get("username"),detail=f"memory_id={mid}")
    return jsonify({"ok":True,"memories":list_memories(session["user_id"])})

@app.delete("/api/memories/<int:memory_id>")
def api_memory_delete(memory_id):
    auth_err=require_login_json()
    if auth_err:return auth_err
    if not delete_memory(session["user_id"],memory_id):
        return jsonify({"ok":False,"error":"기억을 찾을 수 없습니다."}),404
    write_audit("memory.delete",user_id=session["user_id"],username=session.get("username"),detail=f"memory_id={memory_id}")
    return jsonify({"ok":True,"memories":list_memories(session["user_id"])})

@app.get("/api/account/export")
def api_account_export():
    auth_err=require_login_json()
    if auth_err:return auth_err
    uid=session["user_id"]; conn=connect()
    user=conn.execute("SELECT id,username,created_at FROM users WHERE id=?",(uid,)).fetchone()
    chats=conn.execute("SELECT id,title,created_at,updated_at FROM chats WHERE user_id=? ORDER BY id",(uid,)).fetchall()
    payload={"user":dict(user) if user else None,"chats":[],"memories":list_memories(uid,500),"exported_at":now()}
    for chat in chats: payload["chats"].append({"chat":dict(chat),"messages":get_messages(chat["id"])})
    conn.close(); write_audit("account.export",user_id=uid,username=session.get("username"))
    return Response(json.dumps(payload,ensure_ascii=False,indent=2),mimetype="application/json",
      headers={"Content-Disposition":'attachment; filename="pick_account_export.json"'})

@app.delete("/api/account")
def api_account_delete():
    auth_err=require_login_json()
    if auth_err:return auth_err
    uid=session["user_id"]; username=session.get("username")
    if current_user_is_admin():return jsonify({"ok":False,"error":"관리자 계정은 이 화면에서 삭제할 수 없습니다."}),400
    password=str((request.get_json(silent=True) or {}).get("password") or "")
    conn=connect(); user=conn.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    if not user or not check_password_hash(user["password_hash"],password):
        conn.close(); return jsonify({"ok":False,"error":"비밀번호가 올바르지 않습니다."}),403
    conn.execute("DELETE FROM users WHERE id=?",(uid,)); conn.commit(); conn.close()
    write_audit("account.delete",user_id=uid,username=username); session.clear()
    return jsonify({"ok":True})

@app.get("/api/admin/audit")
def api_admin_audit():
    auth_err=require_login_json()
    if auth_err:return auth_err
    if not current_user_is_admin():return jsonify({"ok":False,"error":"관리자만 접근할 수 있습니다."}),403
    conn=connect(); rows=conn.execute("SELECT id,user_id,username,event,detail,ip_hint,created_at FROM audit_events ORDER BY id DESC LIMIT 200").fetchall(); conn.close()
    return jsonify({"ok":True,"events":[dict(r) for r in rows]})

@app.get("/api/admin/users")
def api_admin_users():
    auth_err = require_login_json()
    if auth_err: return auth_err
    if not current_user_is_admin():
        return jsonify({"ok":False,"error":"관리자만 접근할 수 있습니다."}),403
    return jsonify({"ok":True,"admin_label":current_admin_label(),"users":list_users_for_admin(session["user_id"])})


@app.post("/api/admin/users/<int:target_id>/promote")
def api_admin_user_promote(target_id):
    auth_err = require_login_json()
    if auth_err: return auth_err
    try:
        promote_admin(session["user_id"], target_id)
        write_audit("admin.promote",user_id=session["user_id"],username=session.get("username"),detail=f"target_user_id={target_id}")
        return jsonify({"ok":True,"users":list_users_for_admin(session["user_id"])})
    except PermissionError as exc:
        return jsonify({"ok":False,"error":str(exc)}),403
    except (ValueError,LookupError) as exc:
        return jsonify({"ok":False,"error":str(exc)}),400


@app.post("/api/admin/users/<int:target_id>/demote")
def api_admin_user_demote(target_id):
    auth_err = require_login_json()
    if auth_err: return auth_err
    try:
        demote_admin(session["user_id"], target_id)
        write_audit("admin.demote",user_id=session["user_id"],username=session.get("username"),detail=f"target_user_id={target_id}")
        return jsonify({"ok":True,"users":list_users_for_admin(session["user_id"])})
    except PermissionError as exc:
        return jsonify({"ok":False,"error":str(exc)}),403
    except (ValueError,LookupError) as exc:
        return jsonify({"ok":False,"error":str(exc)}),400


@app.get("/api/diagnostics")
def api_diagnostics():
    auth_err = require_login_json()
    if auth_err: return auth_err
    import shutil as _shutil
    result={"ok":True,"database":False,"ollama":False,"models":[],"disk":{},"queue":guard.status(),"schema_version":migrations.LATEST_SCHEMA,"time":accurate_time_status().to_dict()}
    try:
        conn=connect(); conn.execute("SELECT 1").fetchone(); conn.close()
        result["database"]=True
    except Exception as exc: result["database_error"]=str(exc)
    try:
        result["models"]=ollama_health(); result["ollama"]=True
    except Exception as exc: result["ollama_error"]=str(exc)
    try:
        u=_shutil.disk_usage(str(DATA_DIR))
        result["disk"]={"total_gb":round(u.total/1073741824,1),"free_gb":round(u.free/1073741824,1),"used_percent":round(u.used/u.total*100,1)}
    except Exception: pass
    return jsonify(result)

@app.patch("/api/chat/<int:chat_id>/message/<int:message_id>")
def api_message_edit(chat_id,message_id):
    auth_err=require_login_json()
    if auth_err: return auth_err
    uid=session["user_id"]
    if not user_owns_chat(chat_id,uid): return jsonify({"ok":False,"error":"채팅을 찾을 수 없습니다."}),404
    content=str((request.get_json(silent=True) or {}).get("content") or "").strip()
    if not content: return jsonify({"ok":False,"error":"내용을 입력해 주세요."}),400
    conn=connect()
    row=conn.execute("SELECT id,role FROM chat_messages WHERE id=? AND chat_id=?",(message_id,chat_id)).fetchone()
    if not row or row["role"]!="user":
        conn.close(); return jsonify({"ok":False,"error":"사용자 메시지만 수정할 수 있습니다."}),400
    conn.execute("UPDATE chat_messages SET content=? WHERE id=?",(content,message_id))
    conn.execute("DELETE FROM chat_messages WHERE chat_id=? AND id>?",(chat_id,message_id))
    conn.execute("UPDATE chats SET updated_at=? WHERE id=?",(now(),chat_id))
    conn.commit(); conn.close()
    return jsonify({"ok":True,"messages":get_messages(chat_id)})

@app.get("/api/chat/<int:chat_id>/memory")
def api_chat_memory(chat_id):
    auth_err=require_login_json()
    if auth_err: return auth_err
    uid=session["user_id"]
    if not user_owns_chat(chat_id,uid): return jsonify({"ok":False,"error":"채팅을 찾을 수 없습니다."}),404
    messages=get_messages(chat_id)
    return jsonify({"ok":True,"memory":[m["content"] for m in messages if m["role"]=="user"][-8:],"message_count":len(messages)})







@app.get("/api/time/status")
def api_time_status():
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    force = request.args.get("refresh") == "1"
    info = refresh_offset(force=True) if force else accurate_time_status()
    timezone_name = validate_timezone(request.args.get("timezone"), "Asia/Seoul")
    locale_country = (request.args.get("country") or "").upper() or None
    country_info = resolve_country(timezone_name, locale_country)

    return jsonify({
        "ok": True,
        "utc": utc_now().isoformat(timespec="seconds"),
        "time": info.to_dict(),
        "timezone": timezone_name,
        "country": country_info,
    })

@app.get("/api/seasonal-mode")
def api_seasonal_mode_get():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    user_timezone = validate_timezone(request.args.get("timezone"), "Asia/Seoul")
    country = (request.args.get("country") or "").upper() or None
    seasonal_override = get_user_settings(session["user_id"]).get("seasonal_override", "auto")
    mode = resolve_mode(
        session["user_id"], user_timezone=user_timezone, country=country,
        override=seasonal_override,
    )
    return jsonify({
        "ok": True,
        "mode": mode.to_dict(),
        "modes": list_seasonal_modes(),
    })



@app.post("/api/question/orchestrate")
def api_question_orchestrate():
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("message") or "").strip()
    chat_id = payload.get("chat_id")

    history = []
    if chat_id:
        try:
            chat_id = int(chat_id)
            if user_owns_chat(chat_id, session["user_id"]):
                history = get_messages(chat_id)[-12:]
        except Exception:
            history = []

    result = orchestrate(text, history)
    return jsonify({"ok": True, "result": result.to_dict()})

@app.post("/api/question/analyze")
def api_question_analyze():
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("message") or "").strip()
    chat_id = payload.get("chat_id")

    history = []
    if chat_id:
        try:
            chat_id = int(chat_id)
            if user_owns_chat(chat_id, session["user_id"]):
                history = get_messages(chat_id)[-8:]
        except Exception:
            history = []

    analysis = analyze_question(text, history)
    return jsonify({"ok": True, "analysis": analysis.to_dict()})

@app.post("/api/learning/feedback")
def api_learning_feedback():
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    payload = request.get_json(silent=True) or {}
    chat_id = int(payload.get("chat_id") or 0)
    message_id = payload.get("message_id")
    rating = int(payload.get("rating") or 0)
    answer = str(payload.get("assistant_answer") or "")
    note = str(payload.get("note") or "")

    if rating not in (-1, 1):
        return jsonify({"ok": False, "error": "평가는 좋아요 또는 싫어요만 가능합니다."}), 400
    if not chat_id or not user_owns_chat(chat_id, session["user_id"]):
        return jsonify({"ok": False, "error": "채팅을 찾을 수 없습니다."}), 404

    fid = add_feedback(
        session["user_id"], chat_id, message_id,
        rating, answer, note
    )
    auto_approved = False
    if rating == 1:
        auto_approved = bool(approve_feedback(session["user_id"], fid))
    return jsonify({
        "ok": True,
        "feedback_id": fid,
        "auto_approved": auto_approved,
        "stats": training_stats(session["user_id"])
    })


@app.post("/api/learning/feedback/<int:feedback_id>/approve")
def api_learning_approve(feedback_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    if not approve_feedback(session["user_id"], feedback_id):
        return jsonify({"ok": False, "error": "피드백을 찾을 수 없습니다."}), 404

    return jsonify({
        "ok": True,
        "stats": training_stats(session["user_id"])
    })


@app.get("/api/learning")
def api_learning_status():
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    return jsonify({
        "ok": True,
        "stats": training_stats(session["user_id"]),
        "feedback": list_feedback(session["user_id"], 100),
    })


@app.get("/api/learning/export")
def api_learning_export():
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    data = export_jsonl(session["user_id"])
    return Response(
        data,
        mimetype="application/x-ndjson",
        headers={
            "Content-Disposition": 'attachment; filename="pick_training.jsonl"'
        }
    )


@app.post("/api/learning/rebuild-memory-index")
def api_learning_rebuild_index():
    auth_err = require_login_json()
    if auth_err:
        return auth_err

    count = rebuild_user_index(session["user_id"])
    return jsonify({
        "ok": True,
        "indexed_memories": count
    })

@app.get("/api/languages")
def api_languages():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    return jsonify({
        "ok": True,
        "languages": SUPPORTED_LANGUAGES,
        "selected": get_preferred_language(session["user_id"]),
    })


@app.post("/api/language")
def api_language_save():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    payload = request.get_json(silent=True) or {}
    language = str(payload.get("language") or "auto")
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"ok": False, "error": "지원하지 않는 언어입니다."}), 400

    conn = connect()
    conn.execute(
        "UPDATE users SET preferred_language=? WHERE id=?",
        (language, session["user_id"])
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "language": language})

@app.get("/api/models")
def api_models():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    try:
        models = ollama_health()
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc), "models": []}), 503
    return jsonify({
        "ok": True,
        "models": models,
        "selected_model": get_user_settings(session["user_id"]).get("selected_model", "auto"),
    })


@app.get("/api/settings")
def api_settings_get():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    return jsonify({"ok": True, "settings": get_user_settings(session["user_id"])})


@app.post("/api/settings")
def api_settings_save():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    payload = request.get_json(silent=True) or {}
    selected_model = str(payload.get("selected_model", "auto")).strip()[:100] or "auto"
    web_mode = str(payload.get("web_mode", "auto")).strip().lower()
    if web_mode not in {"auto", "always", "off"}:
        web_mode = "auto"
    compact_mode = 1 if payload.get("compact_mode") else 0
    seasonal_override = str(payload.get("seasonal_override", "auto")).strip() or "auto"
    if seasonal_override not in {"auto", *list_seasonal_modes().keys()}:
        seasonal_override = "auto"

    if selected_model != "auto":
        try:
            if selected_model not in ollama_health():
                return jsonify({"ok": False, "error": "선택한 모델이 미니PC에 설치되어 있지 않습니다."}), 400
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Ollama 모델을 확인하지 못했습니다: {exc}"}), 503

    conn = connect()
    conn.execute(
        """INSERT INTO user_settings(user_id,selected_model,web_mode,compact_mode,seasonal_override,updated_at)
           VALUES(?,?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
             selected_model=excluded.selected_model,
             web_mode=excluded.web_mode,
             compact_mode=excluded.compact_mode,
             seasonal_override=excluded.seasonal_override,
             updated_at=excluded.updated_at""",
        (session["user_id"], selected_model, web_mode, compact_mode, seasonal_override, now())
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "settings": get_user_settings(session["user_id"])})


@app.get("/api/chats/search")
def api_chat_search():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    q = str(request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": True, "chats": get_chats(session["user_id"])})
    conn = connect()
    like = f"%{q}%"
    rows = conn.execute(
        """SELECT DISTINCT c.id,c.user_id,c.title,c.created_at,c.updated_at
           FROM chats c
           LEFT JOIN chat_messages m ON m.chat_id=c.id
           WHERE c.user_id=? AND (c.title LIKE ? OR m.content LIKE ?)
           ORDER BY datetime(c.updated_at) DESC, c.id DESC
           LIMIT 50""",
        (session["user_id"], like, like)
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "chats": [dict(r) for r in rows]})


@app.get("/api/chat/<int:chat_id>/export")
def api_chat_export(chat_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    if not assert_chat_owner(chat_id, uid):
        return jsonify({"ok": False, "error": "채팅을 찾을 수 없습니다."}), 404

    conn = connect()
    chat = conn.execute(
        "SELECT id,title,created_at,updated_at FROM chats WHERE id=? AND user_id=?",
        (chat_id, uid)
    ).fetchone()
    conn.close()
    messages = get_messages(chat_id)
    fmt = str(request.args.get("format") or "md").lower()

    if fmt == "json":
        body = json.dumps(
            {"chat": dict(chat), "messages": messages},
            ensure_ascii=False, indent=2
        )
        return Response(
            body,
            mimetype="application/json",
            headers={"Content-Disposition": f'attachment; filename="pick_chat_{chat_id}.json"'}
        )

    parts = [f"# {chat['title']}", ""]
    for m in messages:
        who = "사용자" if m["role"] == "user" else "PICK"
        parts.extend([f"## {who}", "", m["content"], ""])
    return Response(
        "\n".join(parts),
        mimetype="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="pick_chat_{chat_id}.md"'}
    )


@app.post("/api/chat/<int:chat_id>/attachment")
def api_chat_attachment(chat_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    if not assert_chat_owner(chat_id, uid):
        return jsonify({"ok": False, "error": "채팅을 찾을 수 없습니다."}), 404
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "파일이 없습니다."}), 400

    suffix = Path(f.filename or "").suffix.lower()
    attachment_mode = str(request.args.get("mode") or "analysis").strip().lower()
    target_language = str(request.args.get("target_language") or "한국어").strip()[:50] or "한국어"
    try:
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            if attachment_mode == "translate":
                result = translate_image_upload(f, target_language=target_language)
                kind = "image_translation"
            else:
                result = analyze_image_upload(f)
                kind = "image"
        elif suffix in {".mp4", ".mov", ".mkv", ".avi", ".webm"}:
            result = analyze_video_upload(f)
            kind = "video"
        else:
            result = analyze_document_upload(f)
            kind = "file"
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    summary = result.get("analysis") if isinstance(result, dict) else str(result)
    summary = str(summary or "")
    conn = connect()
    conn.execute(
        "INSERT INTO attachments(chat_id,user_id,original_name,stored_name,kind,summary,created_at) VALUES(?,?,?,?,?,?,?)",
        (chat_id, uid, str(f.filename or "file"), "", kind, summary[:12000], now())
    )
    conn.execute(
        "INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
        (chat_id, "assistant", f"[{kind} 분석]\n{summary}", now())
    )
    conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "kind": kind,
        "result": result,
        "messages": get_messages(chat_id),
        "chats": get_chats(uid),
    })


@app.post("/api/chat/<int:chat_id>/background")
def api_chat_background(chat_id):
    auth_err=require_login_json()
    if auth_err:return auth_err
    uid=session["user_id"]
    if not assert_chat_owner(chat_id,uid): return jsonify({"ok":False,"error":"채팅을 찾을 수 없습니다."}),404
    payload=request.get_json(silent=True) or {}; text=str(payload.get("message") or "").strip()
    if not text:return jsonify({"ok":False,"error":"메시지를 입력해 주세요."}),400
    if len(text)>12000:return jsonify({"ok":False,"error":"메시지가 너무 깁니다."}),400
    if not limiter.allow(client_key(f"chat:{uid}"),RATE_LIMIT_CHAT_PER_MIN,60): return jsonify({"ok":False,"error":"메시지를 너무 빠르게 보내고 있습니다."}),429
    c=connect(); cur=c.execute("INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",(chat_id,"user",text,now())); mid=cur.lastrowid
    c.execute("UPDATE chats SET updated_at=? WHERE id=?",(now(),chat_id)); c.commit(); c.close(); update_chat_title(chat_id)
    try: maybe_auto_store(uid,chat_id,text)
    except Exception as e: log("WARNING",f"background memory auto-store: {e}")
    job=enqueue_background_job(uid,chat_id,mid,payload)
    return jsonify({"ok":True,"accepted":True,"job":job,"messages":get_messages(chat_id),"chats":get_chats(uid)}),202

@app.get("/api/jobs/<int:job_id>")
def api_background_job_status(job_id):
    auth_err=require_login_json()
    if auth_err:return auth_err
    job=get_job_for_user(session["user_id"],job_id)
    if not job:return jsonify({"ok":False,"error":"작업을 찾을 수 없습니다."}),404
    return jsonify({"ok":True,"job":job})

@app.post("/api/jobs/<int:job_id>/cancel")
def api_background_job_cancel(job_id):
    auth_err=require_login_json()
    if auth_err:return auth_err
    job=cancel_background_job(session["user_id"],job_id)
    if not job:return jsonify({"ok":False,"error":"작업을 찾을 수 없습니다."}),404
    return jsonify({"ok":True,"job":job})

@app.get("/api/chat/<int:chat_id>/jobs")
def api_background_chat_jobs(chat_id):
    auth_err=require_login_json()
    if auth_err:return auth_err
    uid=session["user_id"]
    if not assert_chat_owner(chat_id,uid):return jsonify({"ok":False,"error":"채팅을 찾을 수 없습니다."}),404
    return jsonify({"ok":True,"jobs":list_chat_jobs(uid,chat_id,active_only=True)})

@app.post("/api/chat/<int:chat_id>/stream")
def api_chat_stream(chat_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    if not assert_chat_owner(chat_id, uid):
        return jsonify({"ok": False, "error": "채팅을 찾을 수 없습니다."}), 404

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("message") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "메시지를 입력해 주세요."}), 400
    if len(text) > 12000:
        return jsonify({"ok": False, "error": "메시지가 너무 깁니다."}), 400
    if not limiter.allow(client_key(f"chat:{uid}"), RATE_LIMIT_CHAT_PER_MIN, 60):
        return jsonify({"ok": False, "error": "메시지를 너무 빠르게 보내고 있습니다."}), 429

    conn = connect()
    conn.execute(
        "INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
        (chat_id, "user", text, now())
    )
    conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
    conn.commit()
    conn.close()
    update_chat_title(chat_id)

    try:
        maybe_auto_store(uid, chat_id, text)
    except Exception as exc:
        log("WARNING", f"memory auto-store: {exc}")

    direct_answer = direct_realtime_or_identity_answer(text, payload)
    if direct_answer is not None:
        direct_text, direct_kind = direct_answer

        @stream_with_context
        def direct_stream():
            conn = connect()
            conn.execute(
                "INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
                (chat_id, "assistant", direct_text, now())
            )
            conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
            conn.commit()
            conn.close()

            try:
                refresh_summary_if_needed(uid, chat_id, get_messages(chat_id), summarizer=None)
            except Exception as exc:
                log("WARNING", f"direct summary refresh: {exc}")

            yield json.dumps({
                "type": "meta",
                "route": {"primary": direct_kind},
                "web_used": direct_kind in {"weather", "news"},
                "web_kind": direct_kind if direct_kind in {"weather", "news"} else None,
            }, ensure_ascii=False) + "\n"
            yield json.dumps({
                "type": "token",
                "text": direct_text,
                "model": "PICK-direct",
            }, ensure_ascii=False) + "\n"
            yield json.dumps({
                "type": "done",
                "model": "PICK-direct",
                "persisted": True,
            }, ensure_ascii=False) + "\n"

        return Response(direct_stream(), mimetype="application/x-ndjson")

    history = get_messages(chat_id)
    recent = [{"role": m["role"], "content": m["content"]} for m in history[:-1][-16:]]

    orchestration = orchestrate(text, recent)
    question_analysis = analyze_question(text, recent)
    normalized_text = orchestration.rewritten_question or question_analysis.normalized or text
    understanding_text = orchestration.understanding_instruction
    route_plan = orchestration.route

    try:
        conversation_summary = get_conversation_summary(uid, chat_id)
    except Exception:
        conversation_summary = ""

    settings = get_user_settings(uid)
    web_mode = settings.get("web_mode", "auto")

    if orchestration.clarification:
        clarification_text = orchestration.clarification

        @stream_with_context
        def clarification_stream():
            yield json.dumps({
                "type": "meta",
                "route": route_plan,
                "clarification": True,
                "web_used": False,
                "web_kind": None,
            }, ensure_ascii=False) + "\n"

            yield json.dumps({
                "type": "token",
                "text": clarification_text,
                "model": "clarification",
            }, ensure_ascii=False) + "\n"

            conn = connect()
            conn.execute(
                "INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
                (chat_id, "assistant", clarification_text, now())
            )
            conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
            conn.commit()
            conn.close()

        return Response(clarification_stream(), mimetype="application/x-ndjson")

    web_context = {}
    web_text = ""
    if WEB_SEARCH_ENABLED and web_mode != "off" and (route_plan.get("use_web") or web_mode == "always"):
        try:
            search_query = text if is_person_query(text) else refine_search_query(question_analysis, recent)
            web_context = web_search(search_query, mode="always")
            web_text = format_web_search(web_context)
        except Exception as exc:
            log("WARNING", f"web search stream: {exc}")

    memory_text = format_memory_context_v2(uid, normalized_text)
    learning_text = format_training_examples(uid, normalized_text, limit=3)
    profile_text = format_profile_context(uid)
    safe_web_text = wrap_untrusted_context("인터넷 검색 자료", web_text) if web_text else ""
    combined_context = "\n\n".join(x for x in [profile_text, memory_text, learning_text, safe_web_text] if x)
    system_extensions = build_system_extensions(uid, normalized_text)
    seasonal_mode = resolve_mode(
        uid,
        user_timezone=(payload.get("timezone") or "Asia/Seoul"),
        country=(str(payload.get("country") or "").upper() or None),
        override=settings.get("seasonal_override", "auto"),
    )
    seasonal_instruction = seasonal_mode.system_instruction if seasonal_mode.active else ""
    extended_context = "\n\n".join(
        x for x in [
            understanding_text,
            ("[Conversation summary]\n" + conversation_summary) if conversation_summary else "",
            seasonal_instruction,
            system_extensions,
            combined_context
        ] if x
    )
    context_limit = 18000 if (
        isinstance(web_context, dict) and web_context.get("kind") in {"news", "person"}
    ) else 10000
    if len(extended_context) > context_limit:
        extended_context = extended_context[-context_limit:]

    prompt = build_prompt(
        normalized_text,
        state={"summary": f"현재 채팅 ID {chat_id}"},
        history=recent,
        web_context=extended_context
    )
    source_rows = _sources_from_web_result(web_context)
    selected_model = choose_model(normalized_text, resolve_selected_model(uid))

    @stream_with_context
    def generate():
        full = []
        try:
            meta = {
                "type": "meta",
                "route": route_plan,
                "seasonal_mode": seasonal_mode.to_dict(),
                "web_used": bool(web_context.get("used")) if isinstance(web_context, dict) else False,
                "web_kind": web_context.get("kind") if isinstance(web_context, dict) else None,
                "sources": source_rows,
            }
            yield json.dumps(meta, ensure_ascii=False) + "\n"
            try:
                with guard.slot():
                    had_error=False
                    for item in stream_generate(prompt, model=selected_model):
                        if item.get("type")=="token": full.append(item.get("text",""))
                        if item.get("type")=="error": had_error=True
                        yield json.dumps(item,ensure_ascii=False)+"\n"
                    guard.failure() if had_error else guard.success()
            except (InferenceBusy,CircuitOpen) as exc:
                yield json.dumps({"type":"error","text":str(exc)},ensure_ascii=False)+"\n"
        finally:
            answer = "".join(full).strip()
            validation = validate_answer(
                answer,
                web_used=bool(web_context.get("used")) if isinstance(web_context, dict) else False,
                coding=bool(route_plan.get("use_coding"))
            )
            answer = validation.cleaned
            if answer:
                conn = connect()
                stored_answer = _attach_source_marker(answer, source_rows)
                conn.execute(
                    "INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
                    (chat_id, "assistant", stored_answer, now())
                )
                conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
                conn.commit()
                conn.close()

                try:
                    refreshed_messages = get_messages(chat_id)
                    refresh_summary_if_needed(uid, chat_id, refreshed_messages, summarizer=None)
                except Exception as exc:
                    log("WARNING", f"conversation summary refresh: {exc}")

    return Response(generate(), mimetype="application/x-ndjson")

@app.post("/api/chat/new")
def api_chat_new():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    chat_id = create_chat(session["user_id"])
    return jsonify({
        "ok": True,
        "chat_id": chat_id,
        "messages": [],
        "chats": get_chats(session["user_id"]),
    })


@app.get("/api/chat/<int:chat_id>")
def api_chat_get(chat_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    if not user_owns_chat(chat_id, uid):
        return jsonify({"ok": False, "error": "채팅을 찾을 수 없습니다."}), 404
    return jsonify({"ok": True, "messages": get_messages(chat_id), "jobs": list_chat_jobs(uid, chat_id, active_only=True)})


@app.post("/api/chat/<int:chat_id>/rename")
def api_chat_rename(chat_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    if not assert_chat_owner(chat_id, uid):
        return jsonify({"ok": False, "error": "채팅을 찾을 수 없습니다."}), 404
    payload = request.get_json(silent=True) or {}
    title = re.sub(r"\s+", " ", str(payload.get("title") or "")).strip()[:60]
    if not title:
        return jsonify({"ok": False, "error": "제목을 입력해 주세요."}), 400
    conn = connect()
    conn.execute(
        "UPDATE chats SET title=?,updated_at=? WHERE id=? AND user_id=?",
        (title, now(), chat_id, uid)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "chats": get_chats(uid)})


@app.post("/api/chat/<int:chat_id>/delete")
def api_chat_delete(chat_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    if not assert_chat_owner(chat_id, uid):
        return jsonify({"ok": False, "error": "채팅을 찾을 수 없습니다."}), 404
    conn = connect()
    conn.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, uid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "chats": get_chats(uid)})


@app.post("/api/chat/<int:chat_id>/send")
def api_chat_send(chat_id):
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    uid = session["user_id"]
    if not assert_chat_owner(chat_id, uid):
        return jsonify({"ok": False, "error": "채팅을 찾을 수 없습니다."}), 404

    if not limiter.allow(
        client_key(f"chat:{uid}"),
        RATE_LIMIT_CHAT_PER_MIN,
        60
    ):
        return jsonify({"ok": False, "error": "메시지를 너무 빠르게 보내고 있습니다. 잠시 후 다시 시도해 주세요."}), 429

    text = str(request.form.get("message") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "메시지를 입력해 주세요."}), 400
    if len(text) > 12000:
        return jsonify({"ok": False, "error": "메시지가 너무 깁니다."}), 400

    conn = connect()
    conn.execute(
        "INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
        (chat_id, "user", text, now())
    )
    conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
    conn.commit()
    conn.close()

    update_chat_title(chat_id)
    history = get_messages(chat_id)
    history_for_llm = [
        {"role": m["role"], "content": m["content"]}
        for m in history[:-1][-16:]
    ]
    orchestration = orchestrate(text, history_for_llm)
    question_analysis = analyze_question(text, history_for_llm)
    normalized_text = orchestration.rewritten_question or question_analysis.normalized or text
    understanding_text = orchestration.understanding_instruction
    settings = get_user_settings(uid)

    web_context = {}
    web_context_text = ""
    if WEB_SEARCH_ENABLED:
        try:
            settings = get_user_settings(uid)
            search_query = text if is_person_query(text) else refine_search_query(question_analysis, history_for_llm)
            web_context = web_search(search_query, mode=("always" if is_person_query(text) else settings.get("web_mode", "auto")))
            web_context_text = format_web_search(web_context)
        except Exception as exc:
            log("WARNING", f"web search: {exc}")

    try:
        system_extensions = build_system_extensions(uid, normalized_text)
        seasonal_mode = resolve_mode(
            uid,
            user_timezone=(request.form.get("timezone") or "Asia/Seoul"),
            country=(str(request.form.get("country") or "").upper() or None),
            override=settings.get("seasonal_override", "auto"),
        )
        seasonal_instruction = seasonal_mode.system_instruction if seasonal_mode.active else ""
        answer = llm.generate(
            normalized_text,
            state={"summary": f"현재 채팅 ID {chat_id}"},
            history=history_for_llm,
            web_context="\n\n".join(
                x for x in [
                    understanding_text,
                    seasonal_instruction,
                    system_extensions,
                    web_context_text
                ] if x
            )
        )
    except Exception as exc:
        log("ERROR", f"chat generation: {exc}")
        answer = "AI 응답을 생성하지 못했습니다. 미니PC의 Ollama 상태를 확인해 주세요."

    source_rows = _sources_from_web_result(web_context)
    stored_answer = _attach_source_marker(answer, source_rows)
    conn = connect()
    conn.execute(
        "INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",
        (chat_id, "assistant", stored_answer, now())
    )
    conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "reply": answer,
        "messages": get_messages(chat_id),
        "chats": get_chats(uid),
        "web_used": bool(web_context.get("used")) if isinstance(web_context, dict) else False,
        "web_kind": web_context.get("kind") if isinstance(web_context, dict) else None,
    })


@app.post("/api/analyze/image")
def api_analyze_image():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "이미지 파일이 없습니다."}), 400
    try:
        mode = str(request.args.get("mode") or "analysis").strip().lower()
        target_language = str(request.args.get("target_language") or "한국어").strip()[:50] or "한국어"
        if mode == "translate":
            return jsonify({"ok": True, "result": translate_image_upload(f, target_language=target_language)})
        return jsonify({"ok": True, "result": analyze_image_upload(f)})
    except Exception as exc:
        log("ERROR", f"image analysis: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/analyze/video")
def api_analyze_video():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "동영상 파일이 없습니다."}), 400
    try:
        return jsonify({"ok": True, "result": analyze_video_upload(f)})
    except Exception as exc:
        log("ERROR", f"video analysis: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/analyze/file")
def api_analyze_file():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "error": "파일이 없습니다."}), 400
    try:
        return jsonify({"ok": True, "result": analyze_document_upload(f)})
    except Exception as exc:
        log("ERROR", f"file analysis: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/generated/<path:filename>")
def generated(filename):
    guard = login_required_view()
    if guard:
        return guard
    safe = Path(filename).name
    return send_from_directory(GENERATED_DIR, safe, as_attachment=True)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = str(request.form.get("username") or "").strip()
    password = str(request.form.get("password") or "").strip()
    password2 = str(request.form.get("password2") or password).strip()

    if has_korean(username) or has_korean(password) or has_korean(password2):
        return render_template("register.html", error="아이디 또는 비밀번호에 한글을 사용할 수 없습니다.")
    if password != password2:
        return render_template("register.html", error="비밀번호 확인이 일치하지 않습니다.")
    if not valid_username(username):
        return render_template("register.html", error="아이디는 영어, 숫자, _, - 만 사용할 수 있으며 2~32자여야 합니다.")
    if not valid_password(password):
        return render_template("register.html", error="비밀번호는 영어, 숫자와 허용된 특수문자를 사용해 4~64자로 입력해 주세요.")

    conn = connect()
    try:
        conn.execute(
            "INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
            (username, generate_password_hash(password), now())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_template("register.html", error="이미 사용 중인 아이디입니다.")
    row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    conn.close()

    session.clear()
    session["user_id"] = row["id"]
    session["username"] = username
    session.permanent = True
    log("INFO", f"registered: {username}")
    write_audit("account.register",user_id=row["id"],username=username,ip_hint=request.remote_addr or "")
    return redirect(url_for("index"))



@app.get("/login/google")
def login_google():
    if not GOOGLE_LOGIN_ENABLED or oauth is None:
        return "Google 로그인이 설정되지 않았습니다.", 503
    redirect_uri = url_for("google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.get("/auth/google/callback")
def google_callback():
    if not GOOGLE_LOGIN_ENABLED or oauth is None:
        return "Google 로그인이 설정되지 않았습니다.", 503

    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo")
        if not userinfo:
            userinfo = oauth.google.userinfo()
    except Exception as exc:
        app.logger.exception("Google OAuth failed")
        return render_template(
            "login.html",
            error=f"Google 로그인에 실패했습니다: {exc}",
            google_enabled=True
        ), 400

    sub = str(userinfo.get("sub") or "").strip()
    email = str(userinfo.get("email") or "").strip()
    name = str(userinfo.get("name") or "").strip()

    if not sub or not email:
        return render_template(
            "login.html",
            error="Google 계정 정보를 확인하지 못했습니다.",
            google_enabled=True
        ), 400

    conn = connect()
    user = conn.execute("SELECT * FROM users WHERE google_sub=?", (sub,)).fetchone()

    if not user:
        # If the same email already exists locally, link Google to that account.
        user = conn.execute("SELECT * FROM users WHERE lower(email)=lower(?)", (email,)).fetchone()

    if user:
        conn.execute(
            "UPDATE users SET google_sub=?,email=?,auth_provider='google' WHERE id=?",
            (sub, email, user["id"])
        )
        user_id = user["id"]
        username = user["username"]
    else:
        base_name = re.sub(r"[^A-Za-z0-9_-]", "", email.split("@")[0])[:24] or "googleuser"
        username = base_name
        suffix = 1
        while conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            suffix += 1
            username = f"{base_name}{suffix}"[:32]

        # Google users do not use the local password to log in.
        random_password = generate_password_hash(os.urandom(32).hex())
        cur = conn.execute(
            """INSERT INTO users(username,password_hash,created_at,email,google_sub,auth_provider,preferred_language)
               VALUES(?,?,?,?,?,'google','auto')""",
            (username, random_password, now(), email, sub)
        )
        user_id = cur.lastrowid

    conn.commit()
    conn.close()

    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session.permanent = True
    write_audit("account.google_login", user_id=user_id, username=username, detail=email)
    return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", google_enabled=GOOGLE_LOGIN_ENABLED)

    if not limiter.allow(
        client_key("login"),
        RATE_LIMIT_LOGIN_PER_10MIN,
        600
    ):
        return render_template("login.html", error="로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.", google_enabled=GOOGLE_LOGIN_ENABLED), 429

    username = str(request.form.get("username") or "").strip()
    password = str(request.form.get("password") or "").strip()

    if has_korean(username) or has_korean(password):
        return render_template("login.html", error="아이디 또는 비밀번호에 한글을 사용할 수 없습니다.", google_enabled=GOOGLE_LOGIN_ENABLED)

    conn = connect()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="아이디 또는 비밀번호가 올바르지 않습니다.", google_enabled=GOOGLE_LOGIN_ENABLED)

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session.permanent = True
    log("INFO", f"login: {username}")
    write_audit("account.login",user_id=user["id"],username=username,ip_hint=request.remote_addr or "")
    return redirect(url_for("index"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.post("/api/admin/backup")
def api_admin_backup():
    auth_err = require_login_json()
    if auth_err:
        return auth_err
    if not current_user_is_admin():
        return jsonify({"ok": False, "error": "관리자만 사용할 수 있습니다."}), 403
    try:
        import backup_db
        backup_db.main()
        return jsonify({"ok": True, "message": "데이터베이스 백업을 완료했습니다."})
    except Exception as exc:
        log("ERROR", f"backup: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 500

@app.get("/admin/status")
def admin_status():
    guard = login_required_view()
    if guard:
        return guard
    if not current_user_is_admin():
        return "관리자만 접근할 수 있습니다.", 403

    conn = connect()
    users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    chats = conn.execute("SELECT COUNT(*) c FROM chats").fetchone()["c"]
    messages = conn.execute("SELECT COUNT(*) c FROM chat_messages").fetchone()["c"]
    logs = conn.execute(
        "SELECT level,message,created_at FROM service_logs ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()

    try:
        models = ollama_health()
        ollama_ok = True
    except Exception as exc:
        models = [str(exc)]
        ollama_ok = False

    return render_template(
        "admin_status.html",
        users=users,
        convs=chats,
        msgs=messages,
        logs=logs,
        ollama_ok=ollama_ok,
        models=models,
        admin_label=current_admin_label()
    )


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
