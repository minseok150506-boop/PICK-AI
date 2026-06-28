
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import re
import sqlite3
import requests
import urllib.parse
import html

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "pick-v9-final-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PICK_DB_PATH", os.path.join(BASE_DIR, "pick_ai.db"))

OLLAMA_HOST = os.environ.get("PICK_OLLAMA_HOST", "http://127.0.0.1:11434").strip().rstrip("/")
OLLAMA_MODEL = os.environ.get("PICK_OLLAMA_MODEL", "qwen3:8b").strip() or "qwen3:8b"
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://pick-ai.onrender.com").strip().rstrip("/")

CREATOR_NAME = "김민석"
SERVICE_NAME = "PICK"
DEFAULT_ADMIN_ID = "minseok"
DEFAULT_ADMIN_PW = "kms0506a!"

SYSTEM_PROMPT = """너는 PICK이다.
너는 김민석님이 만든 개인 AI 챗봇이다.
너의 제작자와 소유자는 김민석님이다.
네이버, OpenAI, Google, Microsoft가 너를 만들었다고 말하지 않는다.
한국어 존댓말로 답한다.
검색 결과가 있으면 검색 결과를 바탕으로 답한다.
검색 결과가 부족하면 부족하다고 말한다.
현재 시간, 전 세계 날씨, 인터넷 검색, 유튜브 검색을 지원한다.
위험하거나 불법적인 요청은 거절하고 안전한 대안을 제시한다.
"""

BAD_WORDS = ["씨발", "시발", "ㅅㅂ", "병신", "ㅂㅅ", "개새끼", "새끼", "좆", "존나", "꺼져", "닥쳐", "죽어"]
HARMFUL_WORDS = ["폭탄", "총기 제작", "마약 제조", "살인 방법", "테러", "랜섬웨어", "악성코드", "바이러스 만들", "계정 해킹", "비밀번호 훔치", "디도스", "ddos"]
ADULT_WORDS = ["야동", "포르노", "성인물", "19금", "성관계", "섹스", "음란"]
SELF_HARM_WORDS = ["자살", "죽고 싶", "죽고싶", "자해", "목매", "극단적 선택"]
SEARCH_HINTS = ["검색", "찾아", "최신", "뉴스", "사이트", "링크", "뭐야", "뜻", "의미", "누구", "설명", "가격", "인터넷", "알려줘", "추천", "비교", "방법", "어디", "언제", "왜", "어떻게"]
WEATHER_HINTS = ["날씨", "기온", "비와", "비 와", "비올", "비 올", "우산", "덥", "추워", "눈와", "눈 와", "weather", "temperature"]
YOUTUBE_HINTS = ["유튜브", "유투브", "youtube", "영상", "쇼츠", "동영상"]
TIME_HINTS = ["몇시", "몇 시", "시간", "날짜", "오늘", "지금", "현재 시간"]
CREATOR_HINTS = ["누가 만들", "제작자", "만든 사람", "개발자", "소유자", "누가 개발"]
TYPO_MAP = {
    "올라마": "Ollama",
    "오라마": "Ollama",
    "올리마": "Ollama",
    "유투브": "유튜브",
    "랜더": "Render",
    "렌더": "Render",
    "클라우드플레어": "Cloudflare",
    "깃허브": "GitHub",
}

WEATHER_CODES = {
    0: "맑음", 1: "대체로 맑음", 2: "부분적으로 흐림", 3: "흐림",
    45: "안개", 48: "서리 안개",
    51: "약한 이슬비", 53: "이슬비", 55: "강한 이슬비",
    61: "약한 비", 63: "비", 65: "강한 비",
    71: "약한 눈", 73: "눈", 75: "강한 눈",
    80: "약한 소나기", 81: "소나기", 82: "강한 소나기",
    95: "뇌우"
}

def now_text():
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")

def normalize(x):
    return str(x or "").strip()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL DEFAULT '새 채팅', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)")
    conn.commit()
    admin = conn.execute("SELECT id FROM users WHERE username=?", (DEFAULT_ADMIN_ID,)).fetchone()
    if not admin:
        conn.execute("INSERT INTO users(username,password_hash,is_admin,created_at) VALUES (?,?,?,?)", (DEFAULT_ADMIN_ID, generate_password_hash(DEFAULT_ADMIN_PW), 1, now_text()))
        conn.commit()
    conn.close()

init_db()

def current_user_id():
    return session.get("user_id")

def is_logged_in():
    return bool(session.get("user_id"))

def username_valid(u):
    return bool(re.fullmatch(r"[A-Za-z0-9_]{3,20}", u or ""))

def has_any(text, words):
    return any(w.lower() in text.lower() for w in words)

def fix_text(text):
    out = text
    for wrong, fixed in TYPO_MAP.items():
        out = out.replace(wrong, fixed)
    return out

def brain(message):
    original = normalize(message)
    fixed = fix_text(original)
    intent = "chat"
    confidence = 0.55
    if has_any(fixed, CREATOR_HINTS):
        intent, confidence = "creator", 0.98
    elif has_any(fixed, WEATHER_HINTS):
        intent, confidence = "weather", 0.96
    elif has_any(fixed, YOUTUBE_HINTS):
        intent, confidence = "youtube", 0.95
    elif has_any(fixed, TIME_HINTS):
        intent, confidence = "time", 0.90
    elif has_any(fixed, SEARCH_HINTS) or (0 < len(fixed) <= 40 and not has_any(fixed, ["안녕", "고마워"])):
        intent, confidence = "search", 0.84

    notes = []
    if fixed != original:
        notes.append(f"오타/표기 보정: {original} → {fixed}")
    if intent in ["search", "youtube"]:
        notes.append("인터넷에서 먼저 찾아보고 답변합니다.")
    if intent == "weather":
        notes.append("전 세계 도시 좌표를 찾아 날씨를 불러옵니다.")
    if intent == "creator":
        notes.append("제작자는 김민석님으로 고정합니다.")
    return {"original": original, "fixed": fixed, "intent": intent, "confidence": confidence, "notes": notes}

def safety_filter(text):
    text = normalize(text)
    if not text:
        return "메시지를 입력해 주세요."
    if re.search(r"sk-[A-Za-z0-9_\-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}", text):
        return "API 키나 비밀 토큰은 입력하지 마세요. 노출된 키는 즉시 폐기하세요."
    if re.search(r"\d{6}[-\s]?[1-4]\d{6}", text):
        return "주민등록번호 같은 민감한 개인정보는 입력하지 마세요."
    if re.search(r"01[016789][-\s]?\d{3,4}[-\s]?\d{4}", text):
        return "전화번호 같은 개인정보는 입력하지 않는 것이 안전합니다."
    if has_any(text, SELF_HARM_WORDS):
        return "지금 매우 힘든 상황일 수 있습니다. 즉시 주변 사람이나 119, 112, 자살예방상담전화 109에 연락하세요."
    if has_any(text, BAD_WORDS):
        return "욕설이 포함된 메시지는 처리하지 않습니다. 표현을 순화해서 다시 입력해 주세요."
    if has_any(text, ADULT_WORDS):
        return "성인 콘텐츠 관련 요청은 지원하지 않습니다."
    if has_any(text, HARMFUL_WORDS):
        return "위험하거나 불법적인 요청은 도와드릴 수 없습니다. 안전하고 합법적인 방향은 도와드릴 수 있습니다."
    return None

def clean_duck_link(link):
    if link.startswith("//duckduckgo.com/l/?uddg="):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse("https:" + link).query)
        return qs.get("uddg", [link])[0]
    return link

def web_search(query):
    try:
        url = "https://duckduckgo.com/html/?q=" + urllib.parse.quote_plus(fix_text(query))
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        r.raise_for_status()
        pattern = re.compile(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', re.S)
        results = []
        for link, title in pattern.findall(r.text)[:8]:
            title = html.unescape(re.sub("<.*?>", "", title)).strip()
            link = clean_duck_link(html.unescape(link).strip())
            if title and link:
                results.append({"title": title, "url": link})
        return results
    except Exception:
        return []

def format_search_results(results):
    if not results:
        return "검색 결과를 가져오지 못했습니다."
    lines = []
    for i, item in enumerate(results, 1):
        lines.append(f"{i}. {item['title']} - {item['url']}")
    return "\n".join(lines)

def youtube_link(query):
    q = fix_text(query)
    for w in ["유튜브", "youtube", "영상", "쇼츠", "찾아줘", "찾아", "검색"]:
        q = q.replace(w, "")
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q.strip() or query)

def weather_place(message):
    s = fix_text(message)
    for w in ["날씨", "기온", "어때", "알려줘", "검색", "현재", "오늘", "내일", "지금", "weather", "temperature", "?", "？"]:
        s = s.replace(w, " ")
    return " ".join(s.split()).strip() or "서울"

def geocode(place):
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search?name=" + urllib.parse.quote_plus(place) + "&count=1&language=ko&format=json"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        results = r.json().get("results") or []
        if not results:
            return None
        x = results[0]
        return {
            "name": x.get("name") or place,
            "country": x.get("country") or "",
            "admin": x.get("admin1") or "",
            "lat": x.get("latitude"),
            "lon": x.get("longitude"),
        }
    except Exception:
        return None

def get_weather(message):
    place = weather_place(message)
    loc = geocode(place) or geocode("서울")
    if not loc:
        return "날씨 위치를 찾지 못했습니다. 도시 이름을 더 정확히 입력해 주세요."
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={loc['lat']}&longitude={loc['lon']}"
        "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&timezone=auto"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        cur = data.get("current", {})
        daily = data.get("daily", {})
        name = loc["name"]
        if loc["admin"]:
            name += f", {loc['admin']}"
        if loc["country"]:
            name += f", {loc['country']}"
        return f"{name} 현재 날씨는 {WEATHER_CODES.get(cur.get('weather_code'), '알 수 없음')}, 기온은 {cur.get('temperature_2m')}℃, 체감온도는 {cur.get('apparent_temperature')}℃, 습도는 {cur.get('relative_humidity_2m')}%, 풍속은 {cur.get('wind_speed_10m')}km/h입니다. 오늘 예상 최저/최고 기온은 {(daily.get('temperature_2m_min') or [None])[0]}℃/{(daily.get('temperature_2m_max') or [None])[0]}℃이고, 강수확률은 {(daily.get('precipitation_probability_max') or [None])[0]}%입니다."
    except Exception:
        return "날씨 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."

def recent_context(chat_id, user_id, limit=10):
    conn = db()
    rows = conn.execute("SELECT role,content FROM messages WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT ?", (chat_id, user_id, limit)).fetchall()
    conn.close()
    lines = []
    for r in reversed(rows):
        lines.append(("사용자" if r["role"] == "user" else "PICK") + ": " + r["content"])
    return "\n".join(lines)

def ask_ollama(message, chat_id=None, user_id=None):
    b = brain(message)
    if b["intent"] == "time":
        return f"현재 시간은 {now_text()}입니다."
    if b["intent"] == "creator":
        return "저는 김민석님이 만든 개인 AI 챗봇 PICK입니다. 네이버가 만든 챗봇이 아닙니다."
    if b["intent"] == "weather":
        return get_weather(b["fixed"])

    external = []
    if b["intent"] == "youtube":
        external.append("유튜브 검색 링크: " + youtube_link(b["fixed"]))

    if b["intent"] in ["search", "youtube"] or b["confidence"] < 0.85:
        results = web_search(b["fixed"])
        external.append("인터넷 검색 결과:\n" + format_search_results(results))

    prompt = SYSTEM_PROMPT
    prompt += f"\n\n현재 날짜와 시간: {now_text()}"
    prompt += f"\n\n정체성: PICK의 제작자와 소유자는 김민석님입니다. 공개 사이트는 {PUBLIC_SITE_URL} 입니다."
    prompt += f"\n\nPICK Brain: 원문={b['original']} / 보정={b['fixed']} / 의도={b['intent']} / 신뢰도={b['confidence']} / 유추={'; '.join(b['notes'])}"
    if chat_id and user_id:
        history = recent_context(chat_id, user_id)
        if history:
            prompt += "\n\n이전 대화:\n" + history
    if external:
        prompt += "\n\n외부 참고 정보:\n" + "\n\n".join(external)
    prompt += f"\n\n사용자 질문: {message}\nPICK:"

    r = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 1200}},
        timeout=300,
    )
    r.raise_for_status()
    return normalize(r.json().get("response", "")) or "잠시 후 다시 시도해 주세요."

def create_chat(user_id, title="새 채팅"):
    conn = db()
    cur = conn.execute("INSERT INTO chats(user_id,title,created_at,updated_at) VALUES (?,?,?,?)", (user_id, title, now_text(), now_text()))
    conn.commit()
    row = conn.execute("SELECT id,title,created_at,updated_at FROM chats WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)

def save_message(chat_id, user_id, role, content):
    conn = db()
    conn.execute("INSERT INTO messages(chat_id,user_id,role,content,created_at) VALUES (?,?,?,?,?)", (chat_id, user_id, role, normalize(content), now_text()))
    conn.execute("UPDATE chats SET updated_at=? WHERE id=? AND user_id=?", (now_text(), chat_id, user_id))
    conn.commit()
    conn.close()

def update_title_once(chat_id, user_id, message):
    conn = db()
    row = conn.execute("SELECT title FROM chats WHERE id=? AND user_id=?", (chat_id, user_id)).fetchone()
    if row and (row["title"] or "").strip() in ("", "새 채팅"):
        conn.execute("UPDATE chats SET title=?, updated_at=? WHERE id=? AND user_id=?", ((normalize(message)[:24] or "새 채팅"), now_text(), chat_id, user_id))
        conn.commit()
    conn.close()

@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def index():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("index.html", username=session.get("username"), public_url=PUBLIC_SITE_URL)

@app.route("/about")
def about():
    return render_template("about.html", public_url=PUBLIC_SITE_URL)

@app.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nAllow: /\n\nSitemap: {PUBLIC_SITE_URL}/sitemap.xml\n", mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap():
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    xml += "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
    xml += f"<url><loc>{PUBLIC_SITE_URL}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>\n"
    xml += f"<url><loc>{PUBLIC_SITE_URL}/about</loc><lastmod>{today}</lastmod><priority>0.8</priority></url>\n"
    xml += "</urlset>"
    return Response(xml, mimetype="application/xml")

@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""
    if request.method == "POST":
        username = normalize(request.form.get("username"))
        password = normalize(request.form.get("password"))
        password2 = normalize(request.form.get("password2"))
        if not username_valid(username):
            error = "아이디는 영문, 숫자, 밑줄만 가능하며 3~20자여야 합니다."
        elif len(password) < 6:
            error = "비밀번호는 6자 이상이어야 합니다."
        elif password != password2:
            error = "비밀번호가 서로 다릅니다."
        else:
            try:
                conn = db()
                conn.execute("INSERT INTO users(username,password_hash,is_admin,created_at) VALUES (?,?,?,?)", (username, generate_password_hash(password), 0, now_text()))
                conn.commit()
                conn.close()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "이미 사용 중인 아이디입니다."
    return render_template("register.html", error=error, public_url=PUBLIC_SITE_URL)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = normalize(request.form.get("username"))
        password = normalize(request.form.get("password"))
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            return redirect(url_for("index"))
        error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render_template("login.html", error=error, public_url=PUBLIC_SITE_URL)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "PICK V9 Final Ollama", "creator": CREATOR_NAME, "model": OLLAMA_MODEL, "time": now_text(), "site": PUBLIC_SITE_URL})

@app.route("/api/status")
def api_status():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        response.raise_for_status()
        return jsonify({"ok": True, "creator": CREATOR_NAME, "model": OLLAMA_MODEL, "host": OLLAMA_HOST, "time": now_text(), "site": PUBLIC_SITE_URL, "ollama": response.json()})
    except Exception as error:
        return jsonify({"ok": False, "creator": CREATOR_NAME, "model": OLLAMA_MODEL, "host": OLLAMA_HOST, "time": now_text(), "error": str(error)})

@app.route("/api/search")
def api_search():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    q = normalize(request.args.get("q"))
    return jsonify({"ok": True, "query": q, "results": web_search(q)})

@app.route("/api/weather")
def api_weather():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    place = normalize(request.args.get("place") or request.args.get("city")) or "서울"
    return jsonify({"ok": True, "weather": get_weather(place + " 날씨")})

@app.route("/api/chats")
def api_chats():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    user_id = current_user_id()
    conn = db()
    rows = conn.execute("SELECT id,title,created_at,updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC", (user_id,)).fetchall()
    conn.close()
    return jsonify({"ok": True, "chats": [dict(row) for row in rows]})

@app.route("/api/chats/new", methods=["POST"])
def api_new_chat():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    return jsonify({"ok": True, "chat": create_chat(current_user_id())})

@app.route("/api/chats/<int:chat_id>/messages")
def api_messages(chat_id):
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    user_id = current_user_id()
    conn = db()
    rows = conn.execute("SELECT id,role,content,created_at FROM messages WHERE chat_id=? AND user_id=? ORDER BY id ASC", (chat_id, user_id)).fetchall()
    conn.close()
    return jsonify({"ok": True, "messages": [dict(row) for row in rows]})

@app.route("/api/chats/<int:chat_id>/send", methods=["POST"])
def api_chat_send(chat_id):
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    user_id = current_user_id()
    message = normalize(request.form.get("message") or (request.get_json(silent=True) or {}).get("message"))
    b = brain(message)
    blocked = safety_filter(message)
    if blocked:
        return jsonify({"ok": True, "filtered": True, "reply": blocked, "brain": b})
    try:
        update_title_once(chat_id, user_id, message)
        save_message(chat_id, user_id, "user", message)
        reply = ask_ollama(message, chat_id, user_id)
        save_message(chat_id, user_id, "assistant", reply)
        return jsonify({"ok": True, "filtered": False, "reply": reply, "brain": b})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "brain": b})

@app.route("/api/chats/<int:chat_id>/delete", methods=["POST"])
def api_delete_chat(chat_id):
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    user_id = current_user_id()
    conn = db()
    conn.execute("DELETE FROM messages WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
