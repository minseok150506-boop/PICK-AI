import time

import os
import re
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


APP_NAME = "PICK"
OWNER_ADMIN_USERNAME = "minseok"
OWNER_ADMIN_PASSWORD = "kms0506a!"
DB_PATH = "data/pick.db"

app = Flask(__name__)
app.secret_key = os.environ.get("PICK_SECRET_KEY", "pick-dev-secret-change-me")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("PICK_COOKIE_SECURE", "1") == "1"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


# -----------------------------
# DB
# -----------------------------
def db():
    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)


    cols = [r["name"] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
    if "is_blocked" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS blocked_ips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT UNIQUE NOT NULL,
        reason TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        ip TEXT NOT NULL,
        success INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        admin_username TEXT,
        action TEXT NOT NULL,
        target TEXT,
        ip TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(chat_id) REFERENCES chats(id)
    )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# Helpers
# -----------------------------
def has_korean(text: str) -> bool:
    return any("가" <= ch <= "힣" or "ㄱ" <= ch <= "ㅎ" or "ㅏ" <= ch <= "ㅣ" for ch in str(text or ""))


def valid_username(username: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_-]{2,32}", username or "") is not None


def valid_password(password: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9!@#$%^&*()_\-+=.?]{4,64}", password or "") is not None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if is_user_blocked(session.get("user_id")):
            session.clear()
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if int(session.get("is_admin") or 0) != 1:
            return render_template("denied.html"), 403
        return fn(*args, **kwargs)
    return wrapper


def clean_reply(text: str) -> str:
    text = str(text or "").strip()
    text = text.replace("Plcker", "PICK").replace("Picker", "PICK").replace("plcker", "PICK")
    return text or "죄송합니다. 응답을 만들지 못했습니다."


def local_ai_reply(user_text: str) -> str:
    t = (user_text or "").strip()

    if any(x in t for x in ["누가 만들", "제작자", "개발자", "만든 사람"]):
        return "PICK은 김민석님이 만든 AI 챗봇 서비스입니다."

    if any(x in t for x in ["너는 누구", "정체", "뭐야"]):
        return "저는 PICK입니다. 김민석님이 만든 한국어 AI 챗봇 서비스입니다."

    if "이미지" in t and any(x in t for x in ["분석", "업로드", "봐"]):
        return "이미지 분석 기능은 다음 단계에서 연결할 수 있습니다. 현재 클린 버전은 채팅, 회원가입, 관리자, DB 저장을 우선 안정화했습니다."

    if "새 채팅" in t:
        return "왼쪽의 새 채팅 버튼을 누르시면 새 대화를 시작할 수 있습니다."

    if "안녕" in t:
        return "안녕하세요. 저는 PICK입니다. 무엇을 도와드릴까요?"

    if "도와" in t:
        return "네, 도와드리겠습니다. 원하는 작업을 구체적으로 말씀해 주세요."

    return f"요청을 확인했습니다. '{t}'에 대해 더 정확히 도와드리려면 원하는 결과를 조금 더 자세히 말씀해 주세요."



# -----------------------------
# Security helpers
# -----------------------------
LOGIN_ATTEMPTS = {}

def client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()

def too_many_login_attempts(username):
    key = f"{client_ip()}:{username}"
    now_ts = time.time()
    attempts = [t for t in LOGIN_ATTEMPTS.get(key, []) if now_ts - t < 300]
    LOGIN_ATTEMPTS[key] = attempts
    return len(attempts) >= 5

def record_login_failure(username):
    key = f"{client_ip()}:{username}"
    LOGIN_ATTEMPTS.setdefault(key, []).append(time.time())

def clear_login_failures(username):
    key = f"{client_ip()}:{username}"
    LOGIN_ATTEMPTS.pop(key, None)

def strong_password(password):
    if not valid_password(password):
        return False
    if len(password) < 8:
        return False
    return any(c.isalpha() for c in password) and any(c.isdigit() for c in password)

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# -----------------------------
# Security / audit helpers
# -----------------------------
LOGIN_ATTEMPTS = {}

def client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()

def is_ip_blocked(ip=None):
    ip = ip or client_ip()
    conn = db()
    row = conn.execute("SELECT id FROM blocked_ips WHERE ip=?", (ip,)).fetchone()
    conn.close()
    return row is not None

def log_login(username, success, message):
    conn = db()
    conn.execute(
        "INSERT INTO login_logs(username, ip, success, message, created_at) VALUES (?, ?, ?, ?, ?)",
        (username, client_ip(), 1 if success else 0, message, now())
    )
    conn.commit()
    conn.close()

def log_admin(action, target=""):
    try:
        conn = db()
        conn.execute(
            "INSERT INTO admin_logs(admin_id, admin_username, action, target, ip, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session.get("user_id"), session.get("username"), action, str(target), client_ip(), now())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def is_user_blocked(user_id):
    try:
        conn = db()
        row = conn.execute("SELECT is_blocked FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return bool(row and int(row["is_blocked"] or 0) == 1)
    except Exception:
        return False

def too_many_login_attempts(username):
    key = f"{client_ip()}:{username}"
    now_ts = time.time()
    attempts = [t for t in LOGIN_ATTEMPTS.get(key, []) if now_ts - t < 300]
    LOGIN_ATTEMPTS[key] = attempts
    return len(attempts) >= 5

def record_login_failure(username):
    key = f"{client_ip()}:{username}"
    LOGIN_ATTEMPTS.setdefault(key, []).append(time.time())

def clear_login_failures(username):
    key = f"{client_ip()}:{username}"
    LOGIN_ATTEMPTS.pop(key, None)

@app.before_request
def block_bad_ip():
    if request.endpoint in {"static"}:
        return
    if is_ip_blocked():
        return "차단된 IP입니다.", 403

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# -----------------------------
# Auth
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", app_name=APP_NAME)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if has_korean(username) or has_korean(password):
        return render_template("register.html", app_name=APP_NAME, error="아이디와 비밀번호에는 한글을 사용할 수 없습니다.")

    if not valid_username(username):
        return render_template("register.html", app_name=APP_NAME, error="아이디는 영어, 숫자, _, - 만 사용할 수 있으며 2~32자여야 합니다.")

    if not strong_password(password):
        return render_template("register.html", app_name=APP_NAME, error="비밀번호는 영어+숫자를 포함해 8자 이상이어야 하며 한글은 사용할 수 없습니다.")

    conn = db()
    # 고정 관리자 계정만 관리자입니다.
    # 아이디 minseok + 비밀번호 kms0506a! 조합만 관리자입니다.
    is_admin = 1 if (username == OWNER_ADMIN_USERNAME and password == OWNER_ADMIN_PASSWORD) else 0

    try:
        conn.execute(
            "INSERT INTO users(username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), is_admin, now())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_template("register.html", app_name=APP_NAME, error="이미 사용 중인 아이디입니다.")

    user = conn.execute("SELECT id, username, is_admin FROM users WHERE username=?", (username,)).fetchone()
    conn.close()

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["is_admin"] = int(user["is_admin"])
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", app_name=APP_NAME)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if too_many_login_attempts(username):
        return render_template("login.html", app_name=APP_NAME, error="로그인 실패가 너무 많습니다. 5분 뒤 다시 시도해 주세요.")

    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        record_login_failure(username)
        return render_template("login.html", app_name=APP_NAME, error="아이디 또는 비밀번호가 올바르지 않습니다.")

    # 고정 관리자 계정은 로그인 시 관리자 권한을 보정합니다.
    if username == OWNER_ADMIN_USERNAME and password == OWNER_ADMIN_PASSWORD and int(user["is_admin"] or 0) != 1:
        conn = db()
        conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (user["id"],))
        conn.commit()
        conn.close()
        user = dict(user)
        user["is_admin"] = 1

    clear_login_failures(username)
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["is_admin"] = int(user["is_admin"] or 0)
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------------
# Pages
# -----------------------------
@app.route("/")
@login_required
def index():
    return render_template(
        "index.html",
        app_name=APP_NAME,
        username=session.get("username"),
        is_admin=int(session.get("is_admin") or 0)
    )


@app.route("/admin")
@admin_required
def admin():
    conn = db()
    users = conn.execute("""
        SELECT 
            u.id, u.username, u.is_admin, u.is_blocked, u.created_at,
            COUNT(DISTINCT c.id) AS chat_count,
            COUNT(m.id) AS message_count
        FROM users u
        LEFT JOIN chats c ON c.user_id = u.id
        LEFT JOIN messages m ON m.chat_id = c.id
        GROUP BY u.id
        ORDER BY u.id ASC
    """).fetchall()
    conn.close()
    return render_template("admin.html", app_name=APP_NAME, users=users)


@app.route("/admin/user/<int:user_id>/admin", methods=["POST"])
@admin_required
def set_admin(user_id):
    action = request.form.get("action")
    value = 1 if action == "grant" else 0

    if user_id == session.get("user_id") and value == 0:
        # 자기 자신의 관리자 권한은 해제할 수 없습니다.
        return redirect(url_for("admin"))

    conn = db()
    conn.execute("UPDATE users SET is_admin=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()
    log_admin("admin_grant" if value else "admin_revoke", f"user_id={user_id}")
    return redirect(url_for("admin"))



@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    if user_id == session.get("user_id"):
        return redirect(url_for("admin"))

    conn = db()
    target = conn.execute("SELECT id, is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if not target:
        conn.close()
        return redirect(url_for("admin"))

    if int(target["is_admin"] or 0) == 1:
        conn.close()
        return redirect(url_for("admin"))

    chat_ids = [r["id"] for r in conn.execute("SELECT id FROM chats WHERE user_id=?", (user_id,)).fetchall()]
    for cid in chat_ids:
        conn.execute("DELETE FROM messages WHERE chat_id=?", (cid,))
    conn.execute("DELETE FROM chats WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/user/<int:user_id>/block", methods=["POST"])
@admin_required
def block_user(user_id):
    action = request.form.get("action")
    value = 1 if action == "block" else 0

    if user_id == session.get("user_id"):
        return redirect(url_for("admin"))

    conn = db()
    target = conn.execute("SELECT id, username, is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if not target:
        conn.close()
        return redirect(url_for("admin"))

    if int(target["is_admin"] or 0) == 1:
        conn.close()
        return redirect(url_for("admin"))

    conn.execute("UPDATE users SET is_blocked=? WHERE id=?", (value, user_id))
    conn.commit()
    conn.close()
    log_admin("user_block" if value else "user_unblock", target["username"])
    return redirect(url_for("admin"))

@app.route("/admin/ip", methods=["GET", "POST"])
@admin_required
def admin_ip():
    conn = db()
    if request.method == "POST":
        ip = request.form.get("ip", "").strip()
        reason = request.form.get("reason", "").strip()
        if ip:
            conn.execute(
                "INSERT OR IGNORE INTO blocked_ips(ip, reason, created_at) VALUES (?, ?, ?)",
                (ip, reason, now())
            )
            conn.commit()
            log_admin("ip_block", ip)
    ips = conn.execute("SELECT * FROM blocked_ips ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_ip.html", app_name=APP_NAME, ips=ips)

@app.route("/admin/ip/<int:ip_id>/delete", methods=["POST"])
@admin_required
def admin_ip_delete(ip_id):
    conn = db()
    row = conn.execute("SELECT ip FROM blocked_ips WHERE id=?", (ip_id,)).fetchone()
    conn.execute("DELETE FROM blocked_ips WHERE id=?", (ip_id,))
    conn.commit()
    conn.close()
    if row:
        log_admin("ip_unblock", row["ip"])
    return redirect(url_for("admin_ip"))

@app.route("/admin/logs")
@admin_required
def admin_logs():
    conn = db()
    login_logs = conn.execute("SELECT * FROM login_logs ORDER BY id DESC LIMIT 100").fetchall()
    admin_logs = conn.execute("SELECT * FROM admin_logs ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return render_template("admin_logs.html", app_name=APP_NAME, login_logs=login_logs, admin_logs=admin_logs)


def get_message_owner(message_id):
    conn = db()
    row = conn.execute("""
        SELECT m.id, m.chat_id, m.role, m.content, c.user_id
        FROM messages m
        JOIN chats c ON c.id = m.chat_id
        WHERE m.id=?
    """, (message_id,)).fetchone()
    conn.close()
    return row


@app.route("/api/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def api_delete_message(message_id):
    row = get_message_owner(message_id)
    if not row:
        return jsonify({"ok": False, "error": "메시지가 없습니다."}), 404

    # 자기 채팅의 메시지만 삭제 가능
    if row["user_id"] != session.get("user_id"):
        return jsonify({"ok": False, "error": "권한이 없습니다."}), 403

    conn = db()
    conn.execute("DELETE FROM messages WHERE id=?", (message_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/messages/<int:message_id>/edit", methods=["POST"])
@login_required
def api_edit_message(message_id):
    new_content = request.form.get("content", "").strip()
    if not new_content:
        return jsonify({"ok": False, "error": "내용이 비어 있습니다."}), 400

    row = get_message_owner(message_id)
    if not row:
        return jsonify({"ok": False, "error": "메시지가 없습니다."}), 404

    # 자기 채팅의 메시지만 수정 가능
    if row["user_id"] != session.get("user_id"):
        return jsonify({"ok": False, "error": "권한이 없습니다."}), 403

    # 사용자 메시지만 수정 가능. AI 답변 수정은 막음.
    if row["role"] != "user":
        return jsonify({"ok": False, "error": "사용자 메시지만 수정할 수 있습니다."}), 403

    conn = db()
    conn.execute("UPDATE messages SET content=? WHERE id=?", (new_content, message_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "content": new_content})


@app.route("/admin/messages/clear", methods=["POST"])
@admin_required
def admin_clear_all_messages():
    conn = db()
    conn.execute("DELETE FROM messages")
    conn.execute("DELETE FROM chats")
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

# -----------------------------
# API
# -----------------------------
@app.route("/api/chats")
@login_required
def api_chats():
    conn = db()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "chats": [dict(r) for r in rows]})


@app.route("/api/chats/new", methods=["POST"])
@login_required
def api_new_chat():
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chats(user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (session["user_id"], "새 채팅", now(), now())
    )
    conn.commit()
    chat_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "chat": {"id": chat_id, "title": "새 채팅"}})


@app.route("/api/chats/<int:chat_id>/messages")
@login_required
def api_messages(chat_id):
    conn = db()
    owner = conn.execute("SELECT id FROM chats WHERE id=? AND user_id=?", (chat_id, session["user_id"])).fetchone()
    if not owner:
        conn.close()
        return jsonify({"ok": False, "error": "권한이 없습니다."}), 403

    rows = conn.execute(
        "SELECT id, role, content, created_at FROM messages WHERE chat_id=? ORDER BY id ASC",
        (chat_id,)
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "messages": [dict(r) for r in rows]})


@app.route("/api/chats/<int:chat_id>/send", methods=["POST"])
@login_required
def api_send(chat_id):
    text = request.form.get("message", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "메시지가 비어 있습니다."}), 400

    conn = db()
    owner = conn.execute("SELECT id FROM chats WHERE id=? AND user_id=?", (chat_id, session["user_id"])).fetchone()
    if not owner:
        conn.close()
        return jsonify({"ok": False, "error": "권한이 없습니다."}), 403

    conn.execute(
        "INSERT INTO messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, "user", text, now())
    )

    reply = clean_reply(local_ai_reply(text))

    conn.execute(
        "INSERT INTO messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, "assistant", reply, now())
    )

    title = text[:20] if text else "새 채팅"
    conn.execute("UPDATE chats SET title=?, updated_at=? WHERE id=?", (title, now(), chat_id))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "reply": reply})


@app.route("/health")
def health():
    return jsonify({"ok": True, "name": APP_NAME})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
