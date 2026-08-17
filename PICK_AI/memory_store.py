from __future__ import annotations
import sqlite3
from database import connect, now

def init_memory_schema():
    conn=connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS memories(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      content TEXT NOT NULL,
      source_chat_id INTEGER,
      importance INTEGER NOT NULL DEFAULT 3,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY(source_chat_id) REFERENCES chats(id) ON DELETE SET NULL
    )""")
    try:
        conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(content,content='memories',content_rowid='id')""")
        conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memories BEGIN
          INSERT INTO memory_fts(rowid,content) VALUES(new.id,new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memories BEGIN
          INSERT INTO memory_fts(memory_fts,rowid,content) VALUES('delete',old.id,old.content);
        END;
        CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memories BEGIN
          INSERT INTO memory_fts(memory_fts,rowid,content) VALUES('delete',old.id,old.content);
          INSERT INTO memory_fts(rowid,content) VALUES(new.id,new.content);
        END;
        """)
    except sqlite3.OperationalError:
        pass
    conn.commit(); conn.close()

def add_memory(user_id,content,source_chat_id=None,importance=3):
    content=" ".join(str(content or "").split()).strip()
    if not content: raise ValueError("기억할 내용이 없습니다.")
    importance=max(1,min(5,int(importance)))
    conn=connect(); cur=conn.execute(
      "INSERT INTO memories(user_id,content,source_chat_id,importance,created_at,updated_at) VALUES(?,?,?,?,?,?)",
      (user_id,content[:4000],source_chat_id,importance,now(),now()))
    mid=cur.lastrowid; conn.commit(); conn.close(); return mid

def list_memories(user_id,limit=100):
    conn=connect(); rows=conn.execute(
      "SELECT id,content,source_chat_id,importance,created_at,updated_at FROM memories WHERE user_id=? ORDER BY importance DESC,datetime(updated_at) DESC LIMIT ?",
      (user_id,max(1,min(limit,500)))).fetchall()
    conn.close(); return [dict(r) for r in rows]

def delete_memory(user_id,memory_id):
    conn=connect(); cur=conn.execute("DELETE FROM memories WHERE id=? AND user_id=?",(memory_id,user_id))
    conn.commit(); ok=cur.rowcount>0; conn.close(); return ok

def search_memories(user_id,query,limit=8):
    q=" ".join(str(query or "").split()).strip()
    if not q: return list_memories(user_id,limit)
    conn=connect()
    try:
        tokens=[t.replace('"',"") for t in q.split() if len(t)>=2][:8]
        match=" OR ".join(f'"{t}"' for t in tokens)
        if match:
            rows=conn.execute("""SELECT m.id,m.content,m.source_chat_id,m.importance,m.created_at,m.updated_at
              FROM memory_fts f JOIN memories m ON m.id=f.rowid
              WHERE m.user_id=? AND memory_fts MATCH ?
              ORDER BY bm25(memory_fts),m.importance DESC LIMIT ?""",(user_id,match,limit)).fetchall()
            conn.close(); return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        pass
    rows=conn.execute("""SELECT id,content,source_chat_id,importance,created_at,updated_at FROM memories
      WHERE user_id=? AND content LIKE ? ORDER BY importance DESC,datetime(updated_at) DESC LIMIT ?""",(user_id,f"%{q}%",limit)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def format_memory_context(user_id,query):
    rows=search_memories(user_id,query,6)
    if not rows: return ""
    return "[사용자가 승인한 장기 기억]\n"+"\n".join("- "+r["content"] for r in rows)

init_memory_schema()
