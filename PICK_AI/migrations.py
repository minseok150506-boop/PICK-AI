from database import connect
LATEST_SCHEMA=6
def migrate():
    conn=connect()
    conn.execute("CREATE TABLE IF NOT EXISTS schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    row=conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
    cur=int(row["value"]) if row and str(row["value"]).isdigit() else 0
    conn.execute("CREATE TABLE IF NOT EXISTS admin_notes(id INTEGER PRIMARY KEY AUTOINCREMENT,note TEXT NOT NULL,created_at TEXT NOT NULL)")
    conn.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version',?)",(str(LATEST_SCHEMA),))
    conn.commit();conn.close();return {"from":cur,"to":LATEST_SCHEMA}
migrate()
