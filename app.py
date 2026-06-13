from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, re, sqlite3, requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "pick-ollama-register-filtered-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("PICK_DB_PATH", os.path.join(BASE_DIR, "pick_ai.db"))

OLLAMA_HOST = os.environ.get("PICK_OLLAMA_HOST", "http://127.0.0.1:11434").strip().rstrip("/")
OLLAMA_MODEL = os.environ.get("PICK_OLLAMA_MODEL", "qwen3:8b").strip() or "qwen3:8b"

DEFAULT_ADMIN_ID = "minseok"
DEFAULT_ADMIN_PW = "kms0506a!"

SYSTEM_PROMPT = """너는 PICK이다.
한국어 존댓말로 자연스럽고 똑똑하게 답한다.
사용자의 오타와 짧은 문장도 최대한 이해한다.
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

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    history = recent_context(chat_id, user_id) if chat_id and user_id else ""
    prompt = SYSTEM_PROMPT
    if history:
        prompt += "\n\n이전 대화:\n" + history
    prompt += f"\n\n사용자: {user_message}\nPICK:"
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.35, "top_p": 0.9, "num_predict": 1200}},
        timeout=300
    )
    response.raise_for_status()
    answer = normalize(response.json().get("response", ""))
    return answer or "잠시 후 다시 시도해 주세요."

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
                is_admin = 1 if username == DEFAULT_ADMIN_ID else 0
                conn.execute("INSERT INTO users(username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)", (username, generate_password_hash(password), is_admin, now_text()))
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
    return jsonify({"ok": True, "service": "PICK Ollama Register Filtered", "model": OLLAMA_MODEL})

@app.route("/api/status")
def api_status():
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        response.raise_for_status()
        return jsonify({"ok": True, "model": OLLAMA_MODEL, "host": OLLAMA_HOST, "ollama": response.json()})
    except Exception as error:
        return jsonify({"ok": False, "model": OLLAMA_MODEL, "host": OLLAMA_HOST, "error": str(error)})

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

@app.route("/api/chat", methods=["POST"])
def api_chat_simple():
    if not is_logged_in():
        return jsonify({"ok": False, "response": "로그인이 필요합니다."}), 401
    data = request.get_json(silent=True) or {}
    message = normalize(data.get("message"))
    blocked = safety_filter(message)
    if blocked:
        return jsonify({"ok": True, "filtered": True, "response": blocked})
    try:
        reply = ask_ollama(message)
        return jsonify({"ok": True, "filtered": False, "response": reply})
    except Exception:
        return jsonify({"ok": False, "response": "AI 서버에 연결하지 못했습니다. Ollama와 Cloudflare Tunnel 상태를 확인해 주세요."})

@app.route("/api/chats/<int:chat_id>/send", methods=["POST"])
def api_chat_send(chat_id):
    if not is_logged_in():
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    user_id = current_user_id()
    message = normalize(request.form.get("message") or (request.get_json(silent=True) or {}).get("message"))
    blocked = safety_filter(message)
    if blocked:
        return jsonify({"ok": True, "filtered": True, "reply": blocked})
    try:
        update_title_once(chat_id, user_id, message)
        save_message(chat_id, user_id, "user", message)
        reply = ask_ollama(message, chat_id, user_id)
        save_message(chat_id, user_id, "assistant", reply)
        return jsonify({"ok": True, "filtered": False, "reply": reply})
    except Exception:
        return jsonify({"ok": False, "error": "AI 서버에 연결하지 못했습니다. Ollama와 Cloudflare Tunnel 상태를 확인해 주세요."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
