from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo
import os, re, sqlite3, requests, urllib.parse, html, math

app = Flask(__name__)
SERPER_API_KEY = "여기에_API키"

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

memory=[]
app.secret_key = os.environ.get("SECRET_KEY", "pick-v5-brain-ollama-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PICK_DB_PATH", os.path.join(BASE_DIR, "pick_ai.db"))

OLLAMA_HOST = os.environ.get("PICK_OLLAMA_HOST", "http://127.0.0.1:11434").strip().rstrip("/")
OLLAMA_MODEL = os.environ.get("PICK_OLLAMA_MODEL", "qwen3:8b").strip() or "qwen3:8b"

DEFAULT_ADMIN_ID = "minseok"
DEFAULT_ADMIN_PW = "kms0506a!"

SYSTEM_PROMPT = """너는 PICK이다.
너는 한국어로 자연스럽고 전문적으로 답하는 개인 AI 챗봇이다.
항상 존댓말을 사용한다.
사용자의 오타와 짧은 문장도 최대한 이해한다.
PICK Brain 분석 결과가 있으면 그 의도와 유추 내용을 참고한다.
현재 날짜와 시간이 필요한 질문에는 제공된 현재 시간을 기준으로 답한다.
인터넷 검색 참고 정보가 있으면 그 내용을 참고해서 답한다.
모르는 단어, 이름, 사이트, 프로그램, 제품은 모른다고 하지 말고 먼저 검색 결과를 바탕으로 설명한다.
유튜브 요청은 직접 재생하지 말고 검색 링크와 찾는 방법을 제공한다.
불필요한 변명, 반복 문구, 과한 안내문은 넣지 않는다.
위험하거나 불법적인 요청은 도와주지 말고 안전한 대안을 제시한다.
"""

BAD_WORDS = ["씨발","시발","ㅅㅂ","병신","ㅂㅅ","개새끼","새끼","좆","ㅈ같","존나","애미","느금마","꺼져","닥쳐","죽어"]
HARMFUL_WORDS = ["폭탄","폭발물","사제총","총기 제작","무기 제작","마약 제조","독극물","살인 방법","테러","랜섬웨어","악성코드","바이러스 만들","해킹툴","계정 해킹","비밀번호 훔치","디도스","ddos"]
ADULT_WORDS = ["야동","포르노","성인물","19금","성관계","섹스","음란"]
SELF_HARM_WORDS = ["자살","죽고 싶","죽고싶","자해","목매","극단적 선택","나 죽을래"]

API_KEY_PATTERNS = [r"sk-[A-Za-z0-9_\-]{20,}", r"sk-svcacct-[A-Za-z0-9_\-]{20,}", r"ghp_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}"]
PHONE_PATTERN = r"01[016789][-\s]?\d{3,4}[-\s]?\d{4}"
KR_RRN_PATTERN = r"\d{6}[-\s]?[1-4]\d{6}"

TYPO_MAP = {
    "올라마": "Ollama",
    "오라마": "Ollama",
    "올리마": "Ollama",
    "유투브": "유튜브",
    "랜더": "Render",
    "렌더": "Render",
    "클라우드플레어": "Cloudflare",
    "깃허브": "GitHub",
    "레더": "Render",
    "인공신경망": "artificial neural network",
}

INTENT_KEYWORDS = {
    "time": ["몇시", "몇 시", "시간", "날짜", "오늘", "지금"],
    "youtube": ["유튜브", "youtube", "영상", "쇼츠", "동영상","채널"],
    "search": ["검색", "찾아", "최신", "뉴스", "사이트", "링크", "뭐야", "뜻", "의미", "누구", "설명", "가격", "날씨"],
    "coding": ["코드", "파이썬", "flask", "render", "github", "오류", "에러", "수정", "파일", "배포"],
    "chat": ["안녕", "고마워", "너", "대화", "말해", "도와"],
}

# PICK Brain: 작은 인공신경망형 의도 분류기
# 외부 AI 라이브러리 없이, 단어 특징 -> 은닉층 -> 의도 점수 구조로 동작합니다.
BRAIN_FEATURES = [
    "시간","날짜","오늘","지금","몇시",
    "유튜브","youtube","영상","쇼츠","채널",
    "검색","찾아","최신","뉴스","링크","사이트","뭐야","뜻","의미",
    "코드","오류","에러","배포","render","github","flask",
    "안녕","고마워","대화",
    "ollama","올라마","올리마","cloudflare"
]

BRAIN_INTENTS = ["time", "youtube", "search", "coding", "chat"]

BRAIN_WEIGHTS = {
    "time":    [2,2,2,2,2, 0,0,0,0, 0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0, 0,0,0],
    "youtube": [0,0,0,0,0, 3,3,2,2, 1,1,0,0,1,1,0,0,0, 0,0,0,0,0,0, 0,0,0, 0,0,0],
    "search":  [0,0,1,1,0, 1,1,1,1, 3,3,2,2,2,2,2,2,2, 0,0,0,0,0,0, 0,0,0, 2,2,2],
    "coding":  [0,0,0,0,0, 0,0,0,0, 0,1,0,0,0,0,0,0,0, 3,3,3,2,3,3, 0,0,0, 2,1,2],
    "chat":    [0,0,0,0,0, 0,0,0,0, 0,0,0,0,0,0,0,0,0, 0,0,0,0,0,0, 3,3,2, 0,0,0],
}
BRAIN_BIAS = {"time": -0.5, "youtube": -0.5, "search": -0.6, "coding": -0.7, "chat": -0.6}

def now_text():
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")

def normalize(text):
    return str(text or "").strip()

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
        conn.execute("INSERT INTO users(username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)", (DEFAULT_ADMIN_ID, generate_password_hash(DEFAULT_ADMIN_PW), 1, now_text()))
        conn.commit()
    conn.close()

init_db()

def current_user_id():
    return session.get("user_id")

def is_logged_in():
    return bool(session.get("user_id"))

def username_valid(username):
    return bool(re.fullmatch(r"[A-Za-z0-9_]{3,20}", username or ""))

def has_any(text, words):
    low = text.lower()
    return any(w.lower() in low for w in words)

def apply_typo_map(message):
    result = message
    for wrong, fixed in TYPO_MAP.items():
        result = result.replace(wrong, fixed)
    return result

def sigmoid(x):
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        return 0 if x < 0 else 1

def pick_brain(message):
    original = normalize(message)
    fixed = apply_typo_map(original)
    low = fixed.lower()

    features = []
    for f in BRAIN_FEATURES:
        features.append(1 if f.lower() in low else 0)

    scores = {}
    for intent in BRAIN_INTENTS:
        raw = BRAIN_BIAS[intent]
        weights = BRAIN_WEIGHTS[intent]
        for x, w in zip(features, weights):
            raw += x * w
        scores[intent] = round(sigmoid(raw), 4)

    # 규칙 보강: 짧은 낯선 단어는 검색 의도
    if len(fixed) <= 30 and " " not in fixed and not has_any(fixed, ["안녕", "고마워"]):
        scores["search"] = max(scores["search"], 0.78)

    intent = max(scores, key=scores.get)
    confidence = scores[intent]

    inference_notes = []
    if fixed != original:
        inference_notes.append(f"오타/표기를 '{original}'에서 '{fixed}'로 보정했습니다.")

    if confidence < 0.55:
        inference_notes.append("의도가 불명확하여 일반 대화로 처리하되, 필요한 경우 검색을 보조합니다.")
        intent = "chat"

    if intent == "search":
        inference_notes.append("모르는 단어 또는 설명 요청으로 보고 인터넷 검색을 함께 사용합니다.")
    elif intent == "youtube":
        inference_notes.append("유튜브/영상 검색 요청으로 판단했습니다.")
    elif intent == "time":
        inference_notes.append("시간 또는 날짜 질문으로 판단했습니다.")
    elif intent == "coding":
        inference_notes.append("개발/오류/배포 관련 질문으로 판단했습니다.")

    return {
        "original": original,
        "fixed": fixed,
        "intent": intent,
        "confidence": confidence,
        "scores": scores,
        "notes": inference_notes
    }

def safety_filter(text):
    text = normalize(text)
    if not text:
        return "메시지를 입력해 주세요."
    for pattern in API_KEY_PATTERNS:
        if re.search(pattern, text):
            return "API 키나 비밀 토큰이 포함된 메시지는 보안상 처리하지 않습니다. 해당 키는 즉시 폐기하고 새로 발급하세요."
    if re.search(KR_RRN_PATTERN, text):
        return "주민등록번호 같은 민감한 개인정보는 입력하지 마세요."
    if re.search(PHONE_PATTERN, text):
        return "전화번호 같은 개인정보는 입력하지 않는 것이 안전합니다. 필요한 경우 일부를 가려서 입력하세요."
    if has_any(text, SELF_HARM_WORDS):
        return "지금 매우 힘든 상황일 수 있습니다. 혼자 해결하려 하지 마시고 즉시 주변 사람이나 119, 112, 또는 자살예방상담전화 109에 연락하세요."
    if has_any(text, BAD_WORDS):
        return "욕설이 포함된 메시지는 처리하지 않습니다. 표현을 순화해서 다시 입력해 주세요."
    if has_any(text, ADULT_WORDS):
        return "성인 콘텐츠 관련 요청은 지원하지 않습니다."
    if has_any(text, HARMFUL_WORDS):
        return "위험하거나 불법적인 요청은 도와드릴 수 없습니다. 대신 안전하고 합법적인 방향의 정보는 도와드릴 수 있습니다."
    return None

def youtube_link(query):
    q = apply_typo_map(query)
    for w in ["유튜브", "youtube", "영상", "쇼츠", "찾아줘", "찾아", "검색"]:
        q = q.replace(w, "")
    q = q.strip() or query
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)

def clean_duck_link(link):
    if link.startswith("//duckduckgo.com/l/?uddg="):
        parsed = urllib.parse.urlparse("https:" + link)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs:
            return qs["uddg"][0]
    return link

def duckduckgo_search(query):
    try:
        q = apply_typo_map(query)
        url = "https://duckduckgo.com/html/?q=" + urllib.parse.quote_plus(q)
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        res.raise_for_status()
        pattern = re.compile(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', re.S)
        out = []
        for link, title in pattern.findall(res.text)[:6]:
            title = html.unescape(re.sub("<.*?>", "", title)).strip()
            link = clean_duck_link(html.unescape(link).strip())
            if title:
                out.append(f"- {title}: {link}")
        return "\n".join(out)
    except Exception:
        return ""

def build_search_context(message, brain):
    fixed = brain["fixed"]
    parts = []
    if brain["fixed"] != brain["original"]:
        parts.append(f"오타/표기 보정: '{brain['original']}' → '{brain['fixed']}'")
    if brain["intent"] == "youtube":
        parts.append("유튜브 검색 링크: " + youtube_link(fixed))
    if brain["intent"] in ["search", "youtube", "coding"]:
        result = duckduckgo_search(fixed)
        if result:
            parts.append("인터넷 검색 결과:\n" + result)
        else:
            parts.append("인터넷 검색 결과를 가져오지 못했습니다. 알려진 범위에서 답하되 불확실하면 명확히 말하세요.")
    return "\n".join(parts)

def recent_context(chat_id, user_id, limit=10):
    conn = db()
    rows = conn.execute("SELECT role, content FROM messages WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT ?", (chat_id, user_id, limit)).fetchall()
    conn.close()
    lines = []
    for row in reversed(rows):
        speaker = "사용자" if row["role"] == "user" else "PICK"
        lines.append(f"{speaker}: {row['content']}")
    return "\n".join(lines)

def ask_ollama(user_message, chat_id=None, user_id=None):
    current_time = now_text()
    brain = pick_brain(user_message)

    if brain["intent"] == "time":
        return f"현재 시간은 {current_time}입니다."

    prompt = SYSTEM_PROMPT + f"\n\n현재 날짜와 시간: {current_time}"
    prompt += "\n\nPICK Brain 분석:"
    prompt += f"\n- 원문: {brain['original']}"
    prompt += f"\n- 보정 질문: {brain['fixed']}"
    prompt += f"\n- 추정 의도: {brain['intent']}"
    prompt += f"\n- 신뢰도: {brain['confidence']}"
    if brain["notes"]:
        prompt += "\n- 유추 내용: " + " / ".join(brain["notes"])

    if chat_id and user_id:
        history = recent_context(chat_id, user_id)
        if history:
            prompt += "\n\n이전 대화:\n" + history

    ctx = build_search_context(user_message, brain)
    if ctx:
        prompt += "\n\n인터넷/유튜브 참고 정보:\n" + ctx

    prompt += f"\n\n사용자 원문: {user_message}"
    if brain["fixed"] != user_message:
        prompt += f"\n보정된 질문: {brain['fixed']}"
    prompt += "\nPICK:"
    internet = web_search(user_message)
    if internet:
        prompt += f"\n\n웹 검색 결과:\n{internet}"
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 1200}
        },
        timeout=300
    )
    response.raise_for_status()
    return normalize(response.json().get("response", "")) or "잠시 후 다시 시도해 주세요."

def create_chat(user_id, title="새 채팅"):
    conn = db()
    cur = conn.execute("INSERT INTO chats(user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)", (user_id, title, now_text(), now_text()))
    conn.commit()
    row = conn.execute("SELECT id, title, created_at, updated_at FROM chats WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)

def save_message(chat_id, user_id, role, content):
    conn = db()
    conn.execute("INSERT INTO messages(chat_id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)", (chat_id, user_id, role, normalize(content), now_text()))
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
    return render_template("index.html", username=session.get("username"))

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
                conn.execute("INSERT INTO users(username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)", (username, generate_password_hash(password), 0, now_text()))
                conn.commit()
                conn.close()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "이미 사용 중인 아이디입니다."
    return render_template("register.html", error=error)

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
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "PICK v5 Brain Ollama", "model": OLLAMA_MODEL, "time": now_text()})

@app.route("/api/status")
def api_status():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        response.raise_for_status()
        return jsonify({"ok": True, "model": OLLAMA_MODEL, "host": OLLAMA_HOST, "time": now_text(), "ollama": response.json()})
    except Exception as error:
        return jsonify({"ok": False, "model": OLLAMA_MODEL, "host": OLLAMA_HOST, "time": now_text(), "error": str(error)})

@app.route("/api/brain", methods=["POST"])
def api_brain():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    data = request.get_json(silent=True) or {}
    message = normalize(data.get("message"))
    return jsonify({"ok": True, "brain": pick_brain(message)})

@app.route("/api/chats")
def api_chats():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    user_id = current_user_id()
    conn = db()
    rows = conn.execute("SELECT id, title, created_at, updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC", (user_id,)).fetchall()
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
    rows = conn.execute("SELECT id, role, content, created_at FROM messages WHERE chat_id=? AND user_id=? ORDER BY id ASC", (chat_id, user_id)).fetchall()
    conn.close()
    return jsonify({"ok": True, "messages": [dict(row) for row in rows]})

@app.route("/api/chats/<int:chat_id>/send", methods=["POST"])
def api_chat_send(chat_id):
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    user_id = current_user_id()
    message = normalize(request.form.get("message") or (request.get_json(silent=True) or {}).get("message"))
    blocked = safety_filter(message)
    if blocked:
        return jsonify({"ok": True, "filtered": True, "reply": blocked, "brain": pick_brain(message)})
    try:
        brain = pick_brain(message)
        update_title_once(chat_id, user_id, message)
        save_message(chat_id, user_id, "user", message)
        reply = ask_ollama(message, chat_id, user_id)
        save_message(chat_id, user_id, "assistant", reply)
        return jsonify({"ok": True, "filtered": False, "reply": reply, "brain": brain})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

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

def web_search(query):

    url="https://google.serper.dev/search"

    headers={
        "X-API-KEY":SERPER_API_KEY,
        "Content-Type":"application/json"
    }

    r=requests.post(
        url,
        headers=headers,
        json={"q":query},
        timeout=20
    )

    result=r.json()

    text=""

    if "organic" in result:

        for item in result["organic"][:5]:

            text+=f"""
제목:{item['title']}

내용:{item['snippet']}

링크:{item['link']}

"""

    return text
