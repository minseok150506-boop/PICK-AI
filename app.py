from openai import OpenAI
import urllib.request
import json
import time

import os
import re
import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Response, Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


APP_NAME = "PICK"
ADMIN_USERNAME_FIXED = "minseok"
ADMIN_PASSWORD_FIXED = "kms0506a!"
OPENAI_MODEL = os.environ.get("PICK_OPENAI_MODEL", "gpt-4o-mini")
OWNER_ADMIN_USERNAME = "minseok"
OWNER_ADMIN_PASSWORD = "kms0506a!"
DB_PATH = "data/pick.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
IS_POSTGRES = bool(DATABASE_URL)

app = Flask(__name__)
app.secret_key = os.environ.get("PICK_SECRET_KEY", "pick-dev-secret-change-me")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("PICK_COOKIE_SECURE", "1") == "1"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


# -----------------------------
# DB
# -----------------------------

class PgConn:
    def __init__(self, url):
        self.conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        sql = q(sql)
        cur.execute(sql, params)
        return cur

    def cursor(self):
        return PgCursor(self)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


class PgCursor:
    def __init__(self, pgconn):
        self.pgconn = pgconn
        self.lastrowid = None
        self._cur = None

    def execute(self, sql, params=()):
        self._cur = self.pgconn.execute(sql, params)
        try:
            if "INSERT INTO" in sql.upper():
                # Not used for PostgreSQL lastrowid except when RETURNING is appended by caller.
                pass
        except Exception:
            pass
        return self

    def fetchone(self):
        return self._cur.fetchone() if self._cur else None

    def fetchall(self):
        return self._cur.fetchall() if self._cur else []

def db():
    if IS_POSTGRES:
        return PgConn(DATABASE_URL)

    Path("data").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def q(sql: str) -> str:
    """SQLite/PostgreSQL 호환 SQL로 변환합니다."""
    if IS_POSTGRES:
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql = sql.replace("?", "%s")
    return sql


def fetch_value(row, key, index=0):
    if row is None:
        return None
    try:
        return row[key]
    except Exception:
        return row[index]



def table_columns(conn, table_name):
    if IS_POSTGRES:
        rows = conn.execute(
            "SELECT column_name AS name FROM information_schema.columns WHERE table_name=%s",
            (table_name,)
        ).fetchall()
        return [r["name"] for r in rows]
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [r["name"] for r in rows]

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


    cols = table_columns(conn, "users")
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



def is_user_blocked(user_id):
    """차단 유저 확인. 함수가 없어서 / 접속 시 500이 나던 문제를 고칩니다."""
    if not user_id:
        return False
    try:
        conn = db()
        row = conn.execute("SELECT is_blocked FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return bool(row and int(row["is_blocked"] or 0) == 1)
    except Exception:
        return False

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
        if not is_fixed_admin_session():
            return render_template("denied.html"), 403
        return fn(*args, **kwargs)
    return wrapper


def clean_reply(text: str) -> str:
    text = str(text or "").strip()
    text = text.replace("Plcker", "PICK").replace("Picker", "PICK").replace("plcker", "PICK")
    return text or "죄송합니다. 응답을 만들지 못했습니다."


def build_conversation_messages(chat_id, user_text: str):
    """DB에 저장된 최근 대화를 읽어 GPT 문맥으로 사용합니다."""
    messages = [
        {
            "role": "system",
            "content": (
                "너는 PICK이라는 한국어 AI 챗봇이다. "
                "제작자는 김민석이다. "
                "항상 한국어 존댓말로 답한다. "
                "사용자의 오타와 발음 실수를 적극적으로 해석한다. "
                "질문을 회피하지 말고 바로 답한다. "
                "모르면 모른다고 말하되, 가능한 대안과 다음 행동을 제시한다. "
                "불필요하게 '더 자세히 말해 달라'고 반복하지 않는다."
            )
        }
    ]

    try:
        conn = db()
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT 16",
            (chat_id,)
        ).fetchall()
        conn.close()

        for r in reversed(rows):
            role = r["role"]
            if role not in ("user", "assistant"):
                continue
            content = str(r["content"] or "").strip()
            if content:
                messages.append({"role": role, "content": content})
    except Exception:
        pass

    messages.append({"role": "user", "content": user_text})
    return messages


def fallback_ai_reply(user_text: str) -> str:
    t = (user_text or "").strip()
    lower = t.lower()

    if not t:
        return "메시지를 입력해 주세요."

    if ("해마" in t and ("이모티콘" in t or "emoji" in lower or "이모지" in t)) or ("seahorse" in lower and "emoji" in lower):
        return "해마 전용 유니코드 이모지는 없습니다. 대신 🐟 🐠 🐡 🐙 🦑 🐚 🌊 같은 바다 관련 이모지를 사용할 수 있습니다."

    if any(x in t for x in ["누가 만들", "제작자", "개발자", "만든 사람"]):
        return "PICK은 김민석님이 만든 AI 챗봇 서비스입니다."

    return f"'{t}'에 대해 답변드리겠습니다. GPT 연결이 아직 설정되지 않았습니다. Render 환경변수에 OPENAI_API_KEY를 넣으면 더 똑똑하게 답변합니다."


def gpt_ai_reply(chat_id, user_text: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return fallback_ai_reply(user_text)

    client = OpenAI(api_key=api_key)
    res = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=build_conversation_messages(chat_id, user_text),
        temperature=0.35,
        max_tokens=1200,
    )
    return clean_reply(res.choices[0].message.content)


def gpt_ai_stream(chat_id, user_text: str):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        yield fallback_ai_reply(user_text)
        return

    client = OpenAI(api_key=api_key)
    stream = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=build_conversation_messages(chat_id, user_text),
        temperature=0.35,
        max_tokens=1200,
        stream=True,
    )

    for chunk in stream:
        try:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
        except Exception:
            continue


def local_ai_reply(user_text: str) -> str:
    # 기존 non-stream API 호환용 fallback
    return fallback_ai_reply(user_text)


def is_fixed_admin_credentials(username, password):
    return username == ADMIN_USERNAME_FIXED and password == ADMIN_PASSWORD_FIXED

def is_fixed_admin_session():
    return session.get("username") == ADMIN_USERNAME_FIXED and int(session.get("is_admin") or 0) == 1

def repair_fixed_admin_user(username, password):
    if not is_fixed_admin_credentials(username, password):
        return None
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        conn.execute(
            "INSERT INTO users(username, password_hash, is_admin, is_blocked, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, generate_password_hash(password), 1, 0, now())
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    else:
        conn.execute("UPDATE users SET is_admin=1, is_blocked=0 WHERE username=?", (username,))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return user

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
    # 관리자 권한은 오직 minseok/kms0506a! 조합에만 부여합니다.
    is_admin = 1 if is_fixed_admin_credentials(username, password) else 0

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
    session["is_admin"] = 1 if user["username"] == ADMIN_USERNAME_FIXED else 0
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
    session["is_admin"] = 1 if user["username"] == ADMIN_USERNAME_FIXED else 0
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
    conn = db()
    user = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
    if user and user["username"] == ADMIN_USERNAME_FIXED:
        conn.execute("UPDATE users SET is_admin=1, is_blocked=0 WHERE id=?", (user_id,))
        conn.commit()
    conn.close()
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
    target = conn.execute("SELECT id, username, is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if not target:
        conn.close()
        return redirect(url_for("admin"))

    if target["username"] == ADMIN_USERNAME_FIXED or int(target["is_admin"] or 0) == 1:
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
                "INSERT INTO blocked_ips(ip, reason, created_at) VALUES (?, ?, ?) ON CONFLICT (ip) DO NOTHING" if IS_POSTGRES else "INSERT OR IGNORE INTO blocked_ips(ip, reason, created_at) VALUES (?, ?, ?)",
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
# Backup / Restore / LLM Admin
# -----------------------------
BACKUP_TABLES = ["users", "chats", "messages", "blocked_ips", "login_logs", "admin_logs"]

def table_exists(conn, table_name):
    try:
        if "IS_POSTGRES" in globals() and IS_POSTGRES:
            row = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_name=?", (table_name,)).fetchone()
            return row is not None
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
        return row is not None
    except Exception:
        return False

def export_backup_data():
    conn = db()
    data = {"app": "PICK", "version": "backup-v1", "created_at": now(), "tables": {}}
    for table in BACKUP_TABLES:
        if table_exists(conn, table):
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data["tables"][table] = [dict(r) for r in rows]
        else:
            data["tables"][table] = []
    conn.close()
    return data

def clear_backup_tables(conn):
    for table in ["messages", "chats", "login_logs", "admin_logs", "blocked_ips", "users"]:
        if table_exists(conn, table):
            conn.execute(f"DELETE FROM {table}")

def restore_backup_data(data, replace=False):
    if not isinstance(data, dict) or "tables" not in data:
        raise ValueError("올바른 백업 파일이 아닙니다.")
    conn = db()
    if replace:
        clear_backup_tables(conn)
    for table in BACKUP_TABLES:
        rows = data.get("tables", {}).get(table, [])
        if not rows or not table_exists(conn, table):
            continue
        for row in rows:
            keys = list(row.keys())
            values = [row[k] for k in keys]
            placeholders = ",".join(["?"] * len(keys))
            columns = ",".join(keys)
            conflict = " ON CONFLICT DO NOTHING" if ("IS_POSTGRES" in globals() and IS_POSTGRES) else ""
            try:
                conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders}){conflict}", values)
            except Exception:
                pass
    conn.commit()
    conn.close()

@app.route("/admin/backup")
@admin_required
def admin_backup_page():
    return render_template("admin_backup.html", app_name=APP_NAME)

@app.route("/admin/backup/download")
@admin_required
def admin_backup_download():
    data = export_backup_data()
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    filename = f"pick_backup_{now().replace(':', '-')}.json"
    return Response(payload, mimetype="application/json", headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.route("/admin/backup/restore", methods=["POST"])
@admin_required
def admin_backup_restore():
    file = request.files.get("backup_file")
    replace = request.form.get("replace") == "1"
    if not file:
        return render_template("admin_backup.html", app_name=APP_NAME, error="백업 파일을 선택해 주세요.")
    try:
        data = json.loads(file.read().decode("utf-8"))
        restore_backup_data(data, replace=replace)
        return render_template("admin_backup.html", app_name=APP_NAME, success="복구가 완료되었습니다.")
    except Exception as e:
        return render_template("admin_backup.html", app_name=APP_NAME, error=f"복구 실패: {e}")

@app.route("/admin/llm")
@admin_required
def admin_llm_page():
    return render_template(
        "admin_llm.html",
        app_name=APP_NAME,
        mode=os.environ.get("PICK_LLM_MODE", "local"),
        ollama_model=os.environ.get("PICK_OLLAMA_MODEL", "qwen2.5:14b"),
        ollama_host=os.environ.get("PICK_OLLAMA_HOST", "http://localhost:11434")
    )


@app.route("/api/chats/<int:chat_id>/stream", methods=["POST"])
@login_required
def api_stream_chat(chat_id):
    text = request.form.get("message", "").strip()
    if not text:
        return Response("data: [ERROR] 메시지가 비어 있습니다.\\n\\n", mimetype="text/event-stream")

    owner = get_owned_chat_or_403(chat_id) if "get_owned_chat_or_403" in globals() else None
    if not owner:
        conn = db()
        owner = conn.execute("SELECT id FROM chats WHERE id=? AND user_id=?", (chat_id, session["user_id"])).fetchone()
        conn.close()

    if not owner:
        return Response("data: [ERROR] 권한이 없습니다.\\n\\n", mimetype="text/event-stream", status=403)

    def generate():
        full_reply = ""
        try:
            conn = db()
            conn.execute(
                "INSERT INTO messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (chat_id, "user", text, now())
            )
            title = text[:20] if text else "새 채팅"
            conn.execute("UPDATE chats SET title=?, updated_at=? WHERE id=?", (title, now(), chat_id))
            conn.commit()
            conn.close()

            for token in gpt_ai_stream(chat_id, text):
                full_reply += token
                safe = token.replace("\\n", "\\\\n")
                yield f"data: {safe}\\n\\n"

            full_reply = clean_reply(full_reply)
            conn = db()
            conn.execute(
                "INSERT INTO messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (chat_id, "assistant", full_reply, now())
            )
            conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now(), chat_id))
            conn.commit()
            conn.close()

            yield "data: [DONE]\\n\\n"
        except Exception as e:
            if not full_reply:
                full_reply = fallback_ai_reply(text)
                conn = db()
                conn.execute(
                    "INSERT INTO messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                    (chat_id, "assistant", full_reply, now())
                )
                conn.commit()
                conn.close()
                yield f"data: {full_reply.replace(chr(10), '\\\\n')}\\n\\n"
            yield "data: [DONE]\\n\\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/admin/fix", methods=["POST"])
@admin_required
def admin_fix_permissions():
    conn = db()
    conn.execute("UPDATE users SET is_admin=0 WHERE username != ?", (ADMIN_USERNAME_FIXED,))
    conn.execute("UPDATE users SET is_admin=1, is_blocked=0 WHERE username = ?", (ADMIN_USERNAME_FIXED,))
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
    if IS_POSTGRES:
        row = conn.execute(
            "INSERT INTO chats(user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?) RETURNING id",
            (session["user_id"], "새 채팅", now(), now())
        ).fetchone()
        chat_id = row["id"]
    else:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chats(user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session["user_id"], "새 채팅", now(), now())
        )
        chat_id = cur.lastrowid
    conn.commit()
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

    reply = clean_reply(gpt_ai_reply(chat_id, text))

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


@app.route("/healthz")
def healthz():
    return {"ok": True, "service": "PICK"}
