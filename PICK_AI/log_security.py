from __future__ import annotations

import base64
import hashlib
import threading
import time

from cryptography.fernet import Fernet, InvalidToken

from config import SECRET_KEY
from database import connect

PREFIX = "enc:v1:"
SETTING_KEY = "log_encryption_enabled_v1"

_SETTING_TTL_SECONDS = 120.0
_setting_lock = threading.Lock()
_setting_value = None
_setting_until = 0.0

_RAW_KEY = hashlib.sha256(
    ("PICK-LOG-ENCRYPTION-V1|" + str(SECRET_KEY)).encode("utf-8")
).digest()
_FERNET = Fernet(base64.urlsafe_b64encode(_RAW_KEY))


def _fernet():
    return _FERNET


def is_encrypted(value):
    return str(value or "").startswith(PREFIX)


def encrypt_value(value):
    text = str(value or "")
    if not text or is_encrypted(text):
        return text
    token = _FERNET.encrypt(text.encode("utf-8")).decode("ascii")
    return PREFIX + token


def decrypt_value(value):
    text = str(value or "")
    if not is_encrypted(text):
        return text
    token = text[len(PREFIX):]
    try:
        return _FERNET.decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError):
        return "[암호화 로그 복호화 실패]"


def _ensure_meta(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_meta("
        "key TEXT PRIMARY KEY,value TEXT NOT NULL)"
    )


def _read_enabled_with_conn(conn):
    _ensure_meta(conn)
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key=?",
        (SETTING_KEY,),
    ).fetchone()
    return True if not row else str(row["value"]).strip() != "0"


def get_log_encryption_enabled(force=False):
    global _setting_value, _setting_until

    current = time.monotonic()
    if not force and _setting_value is not None and current < _setting_until:
        return bool(_setting_value)

    with _setting_lock:
        current = time.monotonic()
        if not force and _setting_value is not None and current < _setting_until:
            return bool(_setting_value)

        conn = connect()
        try:
            value = _read_enabled_with_conn(conn)
        finally:
            conn.close()

        _setting_value = bool(value)
        _setting_until = current + _SETTING_TTL_SECONDS
        return bool(_setting_value)


def set_log_encryption_enabled(enabled):
    global _setting_value, _setting_until

    enabled = bool(enabled)
    conn = connect()
    try:
        _ensure_meta(conn)
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key,value) VALUES(?,?)",
            (SETTING_KEY, "1" if enabled else "0"),
        )
        conn.commit()
    finally:
        conn.close()

    with _setting_lock:
        _setting_value = enabled
        _setting_until = time.monotonic() + _SETTING_TTL_SECONDS

    return enabled


def protect_value(value, enabled=None):
    text = str(value or "")
    if enabled is None:
        enabled = get_log_encryption_enabled()
    return encrypt_value(text) if enabled else text


def protect_service_fields(level, message):
    enabled = get_log_encryption_enabled()
    return (
        protect_value(str(level)[:80], enabled),
        protect_value(str(message)[:4000], enabled),
    )


def protect_audit_fields(username, event, detail, ip_hint):
    enabled = get_log_encryption_enabled()
    return (
        protect_value(str(username or "")[:200], enabled),
        protect_value(str(event or "")[:80], enabled),
        protect_value(str(detail or "")[:4000], enabled),
        protect_value(str(ip_hint or "")[:120], enabled),
    )


def decode_service_row(row):
    d = dict(row)
    d["level"] = decrypt_value(d.get("level"))
    d["message"] = decrypt_value(d.get("message"))
    return d


def decode_audit_row(row):
    d = dict(row)
    for key in ("username", "event", "detail", "ip_hint"):
        d[key] = decrypt_value(d.get(key))
    return d


def get_log_encryption_status():
    conn = connect()
    try:
        _ensure_meta(conn)
        row = conn.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM service_logs "
            " WHERE level LIKE 'enc:v1:%' OR message LIKE 'enc:v1:%') "
            " AS encrypted_service_rows,"
            "(SELECT COUNT(*) FROM audit_events "
            " WHERE username LIKE 'enc:v1:%' OR event LIKE 'enc:v1:%' "
            " OR detail LIKE 'enc:v1:%' OR ip_hint LIKE 'enc:v1:%') "
            " AS encrypted_audit_rows,"
            "(SELECT COUNT(*) FROM service_logs) AS service_rows,"
            "(SELECT COUNT(*) FROM audit_events) AS audit_rows"
        ).fetchone()
        enabled = _read_enabled_with_conn(conn)

        global _setting_value, _setting_until
        with _setting_lock:
            _setting_value = bool(enabled)
            _setting_until = time.monotonic() + _SETTING_TTL_SECONDS

        return {
            "enabled": bool(enabled),
            "encrypted_service_rows": int(row["encrypted_service_rows"] if row else 0),
            "encrypted_audit_rows": int(row["encrypted_audit_rows"] if row else 0),
            "service_rows": int(row["service_rows"] if row else 0),
            "audit_rows": int(row["audit_rows"] if row else 0),
            "scheme": "Fernet/AES128-CBC+HMAC-SHA256",
        }
    finally:
        conn.close()


def migrate_existing_logs(action):
    action = str(action or "").strip().lower()
    if action not in {"encrypt", "decrypt"}:
        raise ValueError("action must be encrypt or decrypt")

    transform = encrypt_value if action == "encrypt" else decrypt_value
    conn = connect()
    try:
        service_rows = conn.execute(
            "SELECT id,level,message FROM service_logs ORDER BY id"
        ).fetchall()
        audit_rows = conn.execute(
            "SELECT id,username,event,detail,ip_hint "
            "FROM audit_events ORDER BY id"
        ).fetchall()

        service_updates = []
        for row in service_rows:
            level = transform(row["level"])
            message = transform(row["message"])
            if level != row["level"] or message != row["message"]:
                service_updates.append((level, message, int(row["id"])))

        audit_updates = []
        for row in audit_rows:
            username = transform(row["username"])
            event = transform(row["event"])
            detail = transform(row["detail"])
            ip_hint = transform(row["ip_hint"])
            if (
                username != row["username"]
                or event != row["event"]
                or detail != row["detail"]
                or ip_hint != row["ip_hint"]
            ):
                audit_updates.append(
                    (username, event, detail, ip_hint, int(row["id"]))
                )

        if service_updates:
            conn.executemany(
                "UPDATE service_logs SET level=?,message=? WHERE id=?",
                service_updates,
            )
        if audit_updates:
            conn.executemany(
                "UPDATE audit_events "
                "SET username=?,event=?,detail=?,ip_hint=? WHERE id=?",
                audit_updates,
            )

        conn.commit()
        return {
            "action": action,
            "service_rows_changed": len(service_updates),
            "audit_rows_changed": len(audit_updates),
        }
    finally:
        conn.close()
