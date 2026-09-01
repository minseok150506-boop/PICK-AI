import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

from config import DB_PATH, ADMIN_USERNAME, ADMIN_PASSWORD


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_TURSO_URL = str(os.environ.get("TURSO_DATABASE_URL") or "").strip()
_TURSO_TOKEN = str(os.environ.get("TURSO_AUTH_TOKEN") or "").strip()
_TURSO_CONFIGURED = bool(_TURSO_URL and _TURSO_TOKEN)
_TURSO_PARTIAL_CONFIG = bool(_TURSO_URL) ^ bool(_TURSO_TOKEN)


class CompatRow:
    __slots__ = ("_values", "_keys", "_exact", "_lower")

    def __init__(self, values, columns):
        self._values = tuple(values)
        self._keys = tuple(str(x) for x in columns)
        self._exact = {k: self._values[i] for i, k in enumerate(self._keys)}
        self._lower = {k.lower(): self._values[i] for i, k in enumerate(self._keys)}

    def __getitem__(self, key):
        if isinstance(key, str):
            if key in self._exact:
                return self._exact[key]
            lowered = key.lower()
            if lowered in self._lower:
                return self._lower[lowered]
            raise IndexError(f"No item with that key: {key}")
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return list(self._keys)

    def items(self):
        return [(k, self._exact[k]) for k in self._keys]

    def get(self, key, default=None):
        try:
            return self[key]
        except (IndexError, KeyError):
            return default

    def __repr__(self):
        return repr(dict(self.items()))


def _description_names(description):
    names = []
    for item in description or ():
        if isinstance(item, (tuple, list)):
            names.append(str(item[0]))
        else:
            name = getattr(item, "name", None)
            names.append(str(name if name is not None else item))
    return names


class RemoteCursor:
    def __init__(self, raw, connection):
        self._raw = raw
        self._connection = connection

    def _wrap(self, row):
        if row is None:
            return None
        if isinstance(row, (CompatRow, sqlite3.Row)):
            return row
        if isinstance(row, dict):
            return CompatRow(tuple(row.values()), tuple(row.keys()))
        names = _description_names(getattr(self._raw, "description", None))
        if names:
            try:
                return CompatRow(tuple(row), names)
            except TypeError:
                pass
        return row

    def execute(self, sql, parameters=()):
        self._raw.execute(sql, parameters)
        return self

    def executemany(self, sql, seq):
        self._raw.executemany(sql, seq)
        return self

    def fetchone(self):
        return self._wrap(self._raw.fetchone())

    def fetchall(self):
        return [self._wrap(row) for row in self._raw.fetchall()]

    def fetchmany(self, size=None):
        rows = self._raw.fetchmany() if size is None else self._raw.fetchmany(size)
        return [self._wrap(row) for row in rows]

    def __iter__(self):
        for row in self._raw:
            yield self._wrap(row)

    @property
    def description(self):
        return getattr(self._raw, "description", None)

    @property
    def rowcount(self):
        return getattr(self._raw, "rowcount", -1)

    @property
    def lastrowid(self):
        value = getattr(self._raw, "lastrowid", None)
        if value not in (None, 0):
            return value
        try:
            row = self._connection.execute("SELECT last_insert_rowid() AS id").fetchone()
            return int(row["id"]) if row else value
        except Exception:
            return value

    def close(self):
        closer = getattr(self._raw, "close", None)
        if closer:
            return closer()

    def __getattr__(self, name):
        return getattr(self._raw, name)


def _split_sql_script(script):
    statements = []
    buffer = ""
    for line in str(script or "").splitlines(True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                statements.append(statement)
            buffer = ""
    if buffer.strip():
        statements.append(buffer.strip())
    return statements


class RemoteConnection:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, parameters=()):
        return RemoteCursor(self._raw.execute(sql, parameters), self)

    def executemany(self, sql, seq):
        cur = self._raw.cursor()
        cur.executemany(sql, seq)
        return RemoteCursor(cur, self)

    def executescript(self, script):
        last = None
        for statement in _split_sql_script(script):
            last = self.execute(statement)
        return last

    def cursor(self):
        return RemoteCursor(self._raw.cursor(), self)

    def commit(self):
        return self._raw.commit()

    def rollback(self):
        return self._raw.rollback()

    def close(self):
        return self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False

    def __getattr__(self, name):
        return getattr(self._raw, name)


def database_status(deep=False):
    result = {
        "mode": "turso-serverless" if _TURSO_CONFIGURED else "sqlite-local",
        "persistent": bool(_TURSO_CONFIGURED),
        "render": bool(os.environ.get("RENDER")),
        "remote_configured": bool(_TURSO_CONFIGURED),
        "partial_configuration": bool(_TURSO_PARTIAL_CONFIG),
        "local_path": str(DB_PATH) if not _TURSO_CONFIGURED else None,
    }
    if _TURSO_URL:
        safe = _TURSO_URL
        if "://" in safe:
            safe = safe.split("://", 1)[1]
        result["remote_host"] = safe.split("/", 1)[0]
    if deep:
        try:
            conn = connect()
            row = conn.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM chats) AS chats,"
                "(SELECT COUNT(*) FROM chat_messages) AS messages"
            ).fetchone()
            result["reachable"] = True
            result["chats"] = int(row["chats"]) if row else 0
            result["messages"] = int(row["messages"]) if row else 0
            conn.close()
        except Exception as exc:
            result["reachable"] = False
            result["error"] = str(exc)[:500]
    return result


def connect():
    if _TURSO_PARTIAL_CONFIG:
        raise RuntimeError(
            "Turso configuration is incomplete. Set both TURSO_DATABASE_URL and TURSO_AUTH_TOKEN."
        )

    if _TURSO_CONFIGURED:
        try:
            import turso_serverless
        except Exception as exc:
            raise RuntimeError(
                "turso_serverless is required. Run pip install turso_serverless."
            ) from exc
        try:
            raw = turso_serverless.connect(
                _TURSO_URL,
                auth_token=_TURSO_TOKEN,
            )
            return RemoteConnection(raw)
        except Exception as exc:
            raise RuntimeError(f"Could not connect PICK to Turso Cloud: {exc}") from exc

    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn



def _columns(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def init_db():
    conn = connect()
    if not _TURSO_CONFIGURED:
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
