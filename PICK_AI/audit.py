from database import connect, now


def init_audit():
    conn = connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,username TEXT,event TEXT NOT NULL,
      detail TEXT NOT NULL DEFAULT '',ip_hint TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL)""")
    conn.commit()
    conn.close()


def write_audit(event, user_id=None, username=None, detail="", ip_hint=""):
    try:
        username_value = str(username or "")[:200]
        event_value = str(event or "")[:80]
        detail_value = str(detail or "")[:4000]
        ip_value = str(ip_hint or "")[:120]

        try:
            from log_security import protect_audit_fields
            username_value, event_value, detail_value, ip_value = protect_audit_fields(
                username_value, event_value, detail_value, ip_value
            )
        except Exception:
            pass

        conn = connect()
        conn.execute(
            "INSERT INTO audit_events(user_id,username,event,detail,ip_hint,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (user_id, username_value, event_value, detail_value, ip_value, now()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


init_audit()
