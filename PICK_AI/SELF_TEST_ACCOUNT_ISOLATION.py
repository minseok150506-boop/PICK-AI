
from pathlib import Path
APP=Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ISO=Path(__file__).with_name("account_isolation.py").read_text(encoding="utf-8")
MEM=Path(__file__).with_name("memory_engine.py").read_text(encoding="utf-8")
PRO=Path(__file__).with_name("account_profile.py").read_text(encoding="utf-8")

checks={
 "chat ownership":"WHERE id=? AND user_id=?" in ISO,
 "message ownership":"JOIN chats c ON c.id=m.chat_id" in ISO and "c.user_id=?" in ISO,
 "attachment ownership":"JOIN chats c ON c.id=a.chat_id" in ISO and "c.user_id=?" in ISO,
 "memory user filter":"WHERE user_id=?" in MEM,
 "profile primary key":"user_id INTEGER PRIMARY KEY" in PRO,
 "session user profile":"format_profile_context(uid)" in APP,
}
for k,v in checks.items():
    if not v: raise SystemExit("FAIL: "+k)
    print(k+": OK")
print("Account isolation self-test complete")
