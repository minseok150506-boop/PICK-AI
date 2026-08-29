import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

from config import DB_PATH, ADMIN_USERNAME, ADMIN_PASSWORD


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _columns(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def init_db():
    conn = connect()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        admin_granted_by INTEGER
    );

    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL DEFAULT '새 채팅',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user','assistant','bot')),
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        selected_model TEXT NOT NULL DEFAULT 'auto',
        web_mode TEXT NOT NULL DEFAULT 'auto',
        compact_mode INTEGER NOT NULL DEFAULT 0,
        seasonal_override TEXT NOT NULL DEFAULT 'auto',
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        original_name TEXT NOT NULL,
        stored_name TEXT NOT NULL,
        kind TEXT NOT NULL,
        summary TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS service_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_chats_user_updated
      ON chats(user_id, updated_at DESC);
    CREATE INDEX IF NOT EXISTS idx_messages_chat_id
      ON chat_messages(chat_id, id);
    CREATE INDEX IF NOT EXISTS idx_attachments_chat
      ON attachments(chat_id, id);
    INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','5');
    """)

    # Migrate old chats table that did not have updated_at.
    
    user_cols = _columns(conn, "users")
    if "email" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "google_sub" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
    if "auth_provider" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'local'")
    if "preferred_language" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN preferred_language TEXT NOT NULL DEFAULT 'auto'")
    if "role" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    if "admin_granted_by" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN admin_granted_by INTEGER")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub) WHERE google_sub IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    chat_cols = _columns(conn, "chats")
    if "updated_at" not in chat_cols:
        conn.execute("ALTER TABLE chats ADD COLUMN updated_at TEXT")
        conn.execute("UPDATE chats SET updated_at=created_at WHERE updated_at IS NULL")

    # Migrate old user_settings schema safely.
    settings_cols = _columns(conn, "user_settings")
    if "selected_model" not in settings_cols:
        conn.execute("ALTER TABLE user_settings ADD COLUMN selected_model TEXT NOT NULL DEFAULT 'auto'")
    if "web_mode" not in settings_cols:
        conn.execute("ALTER TABLE user_settings ADD COLUMN web_mode TEXT NOT NULL DEFAULT 'auto'")
    if "compact_mode" not in settings_cols:
        conn.execute("ALTER TABLE user_settings ADD COLUMN compact_mode INTEGER NOT NULL DEFAULT 0")
    if "seasonal_override" not in settings_cols:
        conn.execute("ALTER TABLE user_settings ADD COLUMN seasonal_override TEXT NOT NULL DEFAULT 'auto'")
    if "updated_at" not in settings_cols:
        conn.execute("ALTER TABLE user_settings ADD COLUMN updated_at TEXT")
        conn.execute("UPDATE user_settings SET updated_at=? WHERE updated_at IS NULL", (now(),))

    # Migrate old attachments schema. This is essential when upgrading an
    # existing PICK database created before account isolation was added.
    attachment_cols = _columns(conn, "attachments")
    if "user_id" not in attachment_cols:
        conn.execute("ALTER TABLE attachments ADD COLUMN user_id INTEGER")
        # Recover ownership from the parent chat instead of guessing.
        conn.execute("""UPDATE attachments
                        SET user_id=(SELECT c.user_id FROM chats c WHERE c.id=attachments.chat_id)
                        WHERE user_id IS NULL""")
    if "stored_name" not in attachment_cols:
        conn.execute("ALTER TABLE attachments ADD COLUMN stored_name TEXT NOT NULL DEFAULT ''")
    if "kind" not in attachment_cols:
        conn.execute("ALTER TABLE attachments ADD COLUMN kind TEXT NOT NULL DEFAULT 'file'")
    if "summary" not in attachment_cols:
        conn.execute("ALTER TABLE attachments ADD COLUMN summary TEXT NOT NULL DEFAULT ''")
    if "created_at" not in attachment_cols:
        conn.execute("ALTER TABLE attachments ADD COLUMN created_at TEXT")
        conn.execute("UPDATE attachments SET created_at=? WHERE created_at IS NULL", (now(),))

    conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_user ON attachments(user_id, id)")

    # Admin account is always available without signup.
    row = conn.execute("SELECT id FROM users WHERE username=?", (ADMIN_USERNAME,)).fetchone()
    hashed = generate_password_hash(ADMIN_PASSWORD)
    if row:
        conn.execute("UPDATE users SET password_hash=?,role='owner',admin_granted_by=NULL WHERE id=?", (hashed, row["id"]))
    else:
        conn.execute(
            "INSERT INTO users(username,password_hash,created_at,role,admin_granted_by) VALUES(?,?,?,?,NULL)",
            (ADMIN_USERNAME, hashed, now(), "owner")
        )

    conn.commit()
    conn.close()


def log(level, message):
    try:
        conn = connect()
        conn.execute(
            "INSERT INTO service_logs(level,message,created_at) VALUES(?,?,?)",
            (str(level), str(message)[:4000], now())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
