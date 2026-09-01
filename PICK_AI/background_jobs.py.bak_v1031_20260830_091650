from __future__ import annotations
import json, os, threading, time
from database import connect, now

class JobCancelled(RuntimeError):
    pass

_started=False
_start_lock=threading.Lock()

def ensure_job_table():
    c=connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS chat_jobs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      chat_id INTEGER NOT NULL,
      user_message_id INTEGER,
      request_json TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued',
      partial_text TEXT NOT NULL DEFAULT '',
      result_text TEXT NOT NULL DEFAULT '',
      stored_text TEXT NOT NULL DEFAULT '',
      sources_json TEXT NOT NULL DEFAULT '[]',
      meta_json TEXT NOT NULL DEFAULT '{}',
      model TEXT NOT NULL DEFAULT '',
      error TEXT NOT NULL DEFAULT '',
      attempts INTEGER NOT NULL DEFAULT 0,
      cancel_requested INTEGER NOT NULL DEFAULT 0,
      answer_message_id INTEGER,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      started_at TEXT,
      finished_at TEXT,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_chat_jobs_status ON chat_jobs(status,id);
    CREATE INDEX IF NOT EXISTS idx_chat_jobs_chat ON chat_jobs(user_id,chat_id,id);
    """)
    c.commit(); c.close()

def _j(v, fallback):
    try: return json.loads(v or "")
    except Exception: return fallback

def public_job(row):
    if not row: return None
    d=dict(row)
    return {
      "id":d["id"],"user_id":d["user_id"],"chat_id":d["chat_id"],
      "user_message_id":d["user_message_id"],"status":d["status"],
      "partial_text":d["partial_text"] or "","result_text":d["result_text"] or "",
      "sources":_j(d["sources_json"],[]),"meta":_j(d["meta_json"],{}),
      "model":d["model"] or "","error":d["error"] or "",
      "attempts":int(d["attempts"] or 0),"cancel_requested":bool(d["cancel_requested"]),
      "answer_message_id":d["answer_message_id"],"created_at":d["created_at"],
      "updated_at":d["updated_at"],"started_at":d["started_at"],"finished_at":d["finished_at"]
    }

def has_active_job(user_id,chat_id):
    ensure_job_table(); c=connect()
    r=c.execute("SELECT 1 FROM chat_jobs WHERE user_id=? AND chat_id=? AND status IN ('queued','running') LIMIT 1",(user_id,chat_id)).fetchone()
    c.close(); return bool(r)

def enqueue_job(user_id,chat_id,user_message_id,payload):
    ensure_job_table(); stamp=now(); c=connect()
    cur=c.execute("""INSERT INTO chat_jobs(user_id,chat_id,user_message_id,request_json,status,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?)""",
                  (user_id,chat_id,user_message_id,json.dumps(payload,ensure_ascii=False),"queued",stamp,stamp))
    jid=cur.lastrowid; c.commit()
    r=c.execute("SELECT * FROM chat_jobs WHERE id=?",(jid,)).fetchone(); c.close()
    return public_job(r)

def get_job_for_user(user_id,job_id):
    ensure_job_table(); c=connect()
    r=c.execute("SELECT * FROM chat_jobs WHERE id=? AND user_id=?",(job_id,user_id)).fetchone(); c.close()
    return public_job(r)

def list_chat_jobs(user_id,chat_id,active_only=True,limit=20):
    ensure_job_table(); c=connect()
    if active_only:
        rows=c.execute("""SELECT * FROM chat_jobs WHERE user_id=? AND chat_id=? AND status IN ('queued','running')
                          ORDER BY id ASC LIMIT ?""",(user_id,chat_id,limit)).fetchall()
    else:
        rows=c.execute("SELECT * FROM chat_jobs WHERE user_id=? AND chat_id=? ORDER BY id DESC LIMIT ?",(user_id,chat_id,limit)).fetchall()
    c.close(); return [public_job(r) for r in rows]

def update_partial(job_id,text,sources=None,model=None,meta=None):
    c=connect()
    c.execute("""UPDATE chat_jobs SET partial_text=?,sources_json=?,model=?,meta_json=?,updated_at=?
                 WHERE id=? AND status='running'""",
              (str(text or "")[-30000:],json.dumps(sources or [],ensure_ascii=False),str(model or ""),
               json.dumps(meta or {},ensure_ascii=False),now(),job_id))
    c.commit(); c.close()

def is_cancel_requested(job_id):
    c=connect(); r=c.execute("SELECT cancel_requested,status FROM chat_jobs WHERE id=?",(job_id,)).fetchone(); c.close()
    return bool(r and (int(r["cancel_requested"] or 0)==1 or r["status"]=="cancelled"))

def _insert_message(c,chat_id,text):
    cur=c.execute("INSERT INTO chat_messages(chat_id,role,content,created_at) VALUES(?,?,?,?)",(chat_id,"assistant",text,now()))
    c.execute("UPDATE chats SET updated_at=? WHERE id=?",(now(),chat_id)); return cur.lastrowid

def cancel_job(user_id,job_id):
    ensure_job_table(); c=connect(); c.execute("BEGIN IMMEDIATE")
    r=c.execute("SELECT * FROM chat_jobs WHERE id=? AND user_id=?",(job_id,user_id)).fetchone()
    if not r: c.rollback(); c.close(); return None
    if r["status"]=="queued":
        mid=_insert_message(c,r["chat_id"],"답변 생성을 취소했습니다.")
        c.execute("""UPDATE chat_jobs SET status='cancelled',cancel_requested=1,answer_message_id=?,
                     finished_at=?,updated_at=? WHERE id=?""",(mid,now(),now(),job_id))
    elif r["status"]=="running":
        c.execute("UPDATE chat_jobs SET cancel_requested=1,updated_at=? WHERE id=?",(now(),job_id))
    c.commit(); r=c.execute("SELECT * FROM chat_jobs WHERE id=?",(job_id,)).fetchone(); c.close(); return public_job(r)

def _recover_stale():
    c=connect(); c.execute("""UPDATE chat_jobs SET status='queued',started_at=NULL,error='',updated_at=?
                 WHERE status='running' AND cancel_requested=0
                 AND datetime(updated_at)<datetime('now','localtime','-3 minutes')""",(now(),)); c.commit(); c.close()

def _claim():
    c=connect()
    try:
        c.execute("BEGIN IMMEDIATE")
        r=c.execute("SELECT * FROM chat_jobs WHERE status='queued' AND cancel_requested=0 ORDER BY id LIMIT 1").fetchone()
        if not r: c.rollback(); return None
        stamp=now(); cur=c.execute("""UPDATE chat_jobs SET status='running',attempts=attempts+1,
                         started_at=COALESCE(started_at,?),updated_at=?,error='' WHERE id=? AND status='queued'""",
                      (stamp,stamp,r["id"]))
        if cur.rowcount!=1: c.rollback(); return None
        c.commit(); rr=c.execute("SELECT * FROM chat_jobs WHERE id=?",(r["id"],)).fetchone(); return dict(rr)
    finally: c.close()

def _heartbeat(job_id,stop):
    while not stop.wait(20):
        try:
            c=connect(); c.execute("UPDATE chat_jobs SET updated_at=? WHERE id=? AND status='running'",(now(),job_id)); c.commit(); c.close()
        except Exception: pass

def _cancelled(job):
    c=connect(); c.execute("BEGIN IMMEDIATE"); r=c.execute("SELECT * FROM chat_jobs WHERE id=?",(job["id"],)).fetchone()
    if r and r["status"] not in ("done","failed","cancelled"):
        mid=r["answer_message_id"] or _insert_message(c,r["chat_id"],"답변 생성을 취소했습니다.")
        c.execute("""UPDATE chat_jobs SET status='cancelled',cancel_requested=1,answer_message_id=?,
                     finished_at=?,updated_at=? WHERE id=?""",(mid,now(),now(),job["id"]))
    c.commit(); c.close()

def _finish(job,result):
    answer=str(result.get("answer") or "").strip(); stored=str(result.get("stored_answer") or answer).strip()
    if not answer: raise RuntimeError("PICK이 빈 답변을 생성했습니다.")
    c=connect(); c.execute("BEGIN IMMEDIATE"); r=c.execute("SELECT * FROM chat_jobs WHERE id=?",(job["id"],)).fetchone()
    if not r: c.rollback(); c.close(); raise RuntimeError("작업을 찾을 수 없습니다.")
    if r["status"]=="done" and r["answer_message_id"]:
        mid=int(r["answer_message_id"]); c.rollback(); c.close(); return mid
    if int(r["cancel_requested"] or 0)==1: c.rollback(); c.close(); raise JobCancelled()
    mid=_insert_message(c,r["chat_id"],stored); stamp=now()
    c.execute("""UPDATE chat_jobs SET status='done',partial_text=?,result_text=?,stored_text=?,sources_json=?,meta_json=?,model=?,
                 error='',answer_message_id=?,finished_at=?,updated_at=? WHERE id=?""",
              (answer,answer,stored,json.dumps(result.get("sources") or [],ensure_ascii=False),json.dumps(result.get("meta") or {},ensure_ascii=False),
               str(result.get("model") or ""),mid,stamp,stamp,r["id"]))
    c.commit(); c.close(); return mid

def _retry_or_fail(job,exc):
    err=str(exc or "알 수 없는 오류")[:1200]; c=connect(); c.execute("BEGIN IMMEDIATE"); r=c.execute("SELECT * FROM chat_jobs WHERE id=?",(job["id"],)).fetchone()
    if not r: c.rollback(); c.close(); return
    if int(r["cancel_requested"] or 0)==1: c.rollback(); c.close(); _cancelled(job); return
    max_attempts=max(1,int(os.environ.get("PICK_BACKGROUND_MAX_ATTEMPTS","3")))
    if int(r["attempts"] or 0)<max_attempts:
        c.execute("UPDATE chat_jobs SET status='queued',error=?,started_at=NULL,updated_at=? WHERE id=?",(err,now(),r["id"])); c.commit(); c.close(); return
    msg=("답변을 백그라운드에서 여러 번 생성하려 했지만 완료하지 못했습니다. 질문은 저장되어 있습니다. "
         "PC의 Ollama와 Cloudflare 연결을 확인한 뒤 다시 질문해 주세요.")
    mid=_insert_message(c,r["chat_id"],msg); stamp=now()
    c.execute("""UPDATE chat_jobs SET status='failed',error=?,result_text=?,answer_message_id=?,finished_at=?,updated_at=? WHERE id=?""",
              (err,msg,mid,stamp,stamp,r["id"])); c.commit(); c.close()

def recover_orphaned_jobs_on_startup():
    ensure_job_table()
    c=connect()
    c.execute("UPDATE chat_jobs SET status='queued',started_at=NULL,error='',updated_at=? WHERE status='running' AND cancel_requested=0",(now(),))
    c.commit(); c.close()

def start_worker(processor,after_complete=None):
    global _started; ensure_job_table(); recover_orphaned_jobs_on_startup()
    with _start_lock:
        if _started: return
        _started=True
    def loop():
        last=0.0
        while True:
            try:
                if time.monotonic()-last>60: _recover_stale(); last=time.monotonic()
                job=_claim()
                if not job: time.sleep(.7); continue
                stop=threading.Event(); threading.Thread(target=_heartbeat,args=(job["id"],stop),daemon=True).start()
                try:
                    if is_cancel_requested(job["id"]): raise JobCancelled()
                    def updater(text,**kwargs):
                        if is_cancel_requested(job["id"]): raise JobCancelled()
                        update_partial(job["id"],text,**kwargs)
                    result=processor(job,updater,lambda:is_cancel_requested(job["id"]))
                    if is_cancel_requested(job["id"]): raise JobCancelled()
                    mid=_finish(job,result)
                    if after_complete:
                        try: after_complete(job,result,mid)
                        except Exception: pass
                except JobCancelled: _cancelled(job)
                except Exception as e: _retry_or_fail(job,e)
                finally: stop.set()
            except Exception: time.sleep(1.2)
    threading.Thread(target=loop,name="pick-background-worker",daemon=True).start()
