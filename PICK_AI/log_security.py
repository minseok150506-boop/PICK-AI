from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from config import SECRET_KEY
from database import connect

PREFIX = "enc:v1:"
SETTING_KEY = "log_encryption_enabled_v1"


def _fernet():
    raw = hashlib.sha256(
        ("PICK-LOG-ENCRYPTION-V1|" + str(SECRET_KEY)).encode("utf-8")
    ).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def is_encrypted(value):
    return str(value or "").startswith(PREFIX)


def encrypt_value(value):
    text = str(value or "")
    if not text or is_encrypted(text):
        return text
    token = _fernet().encrypt(text.encode("utf-8")).decode("ascii")
    return PREFIX + token


def decrypt_value(value):
    text = str(value or "")
    if not is_encrypted(text):
        return text
    token = text[len(PREFIX):]
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError):
        return "[암호화 로그 복호화 실패]"


def _ensure_meta(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_meta("
        "key TEXT PRIMARY KEY,value TEXT NOT NULL)"
    )


def get_log_encryption_enabled():
    conn = connect()
    try:
        _ensure_meta(conn)
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key=?",
            (SETTING_KEY,),
        ).fetchone()
        return True if not row else str(row["value"]).strip() != "0"
    finally:
        conn.close()


def set_log_encryption_enabled(enabled):
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
    return bool(enabled)


def protect_value(value):
    text = str(value or "")
    return encrypt_value(text) if get_log_encryption_enabled() else text


def protect_service_fields(level, message):
    return protect_value(str(level)[:80]), protect_value(str(message)[:4000])


def protect_audit_fields(username, event, detail, ip_hint):
    return (
        protect_value(str(username or "")[:200]),
        protect_value(str(event or "")[:80]),
        protect_value(str(detail or "")[:4000]),
        protect_value(str(ip_hint or "")[:120]),
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
        service = conn.execute(
            "SELECT COUNT(*) AS c FROM service_logs "
            "WHERE level LIKE 'enc:v1:%' OR message LIKE 'enc:v1:%'"
        ).fetchone()
        audit = conn.execute(
            "SELECT COUNT(*) AS c FROM audit_events "
            "WHERE username LIKE 'enc:v1:%' OR event LIKE 'enc:v1:%' "
            "OR detail LIKE 'enc:v1:%' OR ip_hint LIKE 'enc:v1:%'"
        ).fetchone()
        total_service = conn.execute(
            "SELECT COUNT(*) AS c FROM service_logs"
        ).fetchone()
        total_audit = conn.execute(
            "SELECT COUNT(*) AS c FROM audit_events"
        ).fetchone()
        return {
            "enabled": get_log_encryption_enabled(),
            "encrypted_service_rows": int(service["c"] if service else 0),
            "encrypted_audit_rows": int(audit["c"] if audit else 0),
            "service_rows": int(total_service["c"] if total_service else 0),
            "audit_rows": int(total_audit["c"] if total_audit else 0),
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
