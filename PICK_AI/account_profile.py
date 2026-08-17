
from __future__ import annotations
from database import connect, now

def init_schema():
    conn = connect()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS account_profile_memory (
        user_id INTEGER PRIMARY KEY,
        preferred_name TEXT NOT NULL DEFAULT '',
        preferred_language TEXT NOT NULL DEFAULT 'auto',
        response_style TEXT NOT NULL DEFAULT '',
        important_note TEXT NOT NULL DEFAULT '',
        main_project TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()

def get_profile(user_id:int)->dict:
    conn=connect()
    row=conn.execute("SELECT * FROM account_profile_memory WHERE user_id=?",(user_id,)).fetchone()
    if not row:
        conn.execute("""INSERT INTO account_profile_memory(
            user_id,preferred_name,preferred_language,response_style,important_note,main_project,updated_at
        ) VALUES(?,?,?,?,?,?,?)""",(user_id,"","auto","","","",now()))
        conn.commit()
        row=conn.execute("SELECT * FROM account_profile_memory WHERE user_id=?",(user_id,)).fetchone()
    conn.close()
    return dict(row)

def update_profile(user_id:int,payload:dict)->dict:
    current=get_profile(user_id)
    def v(key,limit=2000):
        return str(payload.get(key,current.get(key,"")) or "").strip()[:limit]
    conn=connect()
    conn.execute("""UPDATE account_profile_memory SET
        preferred_name=?,preferred_language=?,response_style=?,important_note=?,main_project=?,updated_at=?
        WHERE user_id=?""",(
        v("preferred_name",200),
        v("preferred_language",40) or "auto",
        v("response_style",1000),
        v("important_note",2000),
        v("main_project",1000),
        now(),user_id
    ))
    conn.commit(); conn.close()
    return get_profile(user_id)

def format_profile_context(user_id:int)->str:
    p=get_profile(user_id)
    lines=[]
    if p.get("preferred_name"): lines.append(f"- 불러줄 이름: {p['preferred_name']}")
    if p.get("preferred_language") and p["preferred_language"]!="auto": lines.append(f"- 기본 언어: {p['preferred_language']}")
    if p.get("response_style"): lines.append(f"- 선호 답변 스타일: {p['response_style']}")
    if p.get("main_project"): lines.append(f"- 주요 프로젝트: {p['main_project']}")
    if p.get("important_note"): lines.append(f"- 꼭 기억할 정보: {p['important_note']}")
    if not lines: return ""
    return "[Private account profile memory]\n현재 로그인한 계정에만 속한 정보입니다.\n"+"\n".join(lines)

init_schema()
