from database import connect, now
def init_audit():
    conn=connect(); conn.execute("""CREATE TABLE IF NOT EXISTS audit_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,username TEXT,event TEXT NOT NULL,
      detail TEXT NOT NULL DEFAULT '',ip_hint TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL)""")
    conn.commit(); conn.close()
def write_audit(event,user_id=None,username=None,detail="",ip_hint=""):
    try:
        conn=connect(); conn.execute("INSERT INTO audit_events(user_id,username,event,detail,ip_hint,created_at) VALUES(?,?,?,?,?,?)",
          (user_id,username,str(event)[:80],str(detail)[:4000],str(ip_hint)[:120],now()))
        conn.commit(); conn.close()
    except Exception: pass
init_audit()
