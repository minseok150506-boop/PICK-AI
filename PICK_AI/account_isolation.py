
from __future__ import annotations
from pathlib import Path
from config import DATA_DIR
from database import connect

def assert_chat_owner(chat_id:int,user_id:int)->bool:
    conn=connect()
    row=conn.execute("SELECT 1 FROM chats WHERE id=? AND user_id=?",(chat_id,user_id)).fetchone()
    conn.close()
    return bool(row)

def assert_message_owner(message_id:int,user_id:int)->bool:
    conn=connect()
    row=conn.execute("""SELECT 1 FROM chat_messages m
        JOIN chats c ON c.id=m.chat_id
        WHERE m.id=? AND c.user_id=?""",(message_id,user_id)).fetchone()
    conn.close()
    return bool(row)

def assert_attachment_owner(attachment_id:int,user_id:int)->bool:
    conn=connect()
    row=conn.execute("""SELECT 1 FROM attachments a
        JOIN chats c ON c.id=a.chat_id
        WHERE a.id=? AND c.user_id=?""",(attachment_id,user_id)).fetchone()
    conn.close()
    return bool(row)

def private_upload_dir(user_id:int)->Path:
    p=DATA_DIR/"users"/str(int(user_id))/"uploads"
    p.mkdir(parents=True,exist_ok=True)
    return p

def private_export_dir(user_id:int)->Path:
    p=DATA_DIR/"users"/str(int(user_id))/"exports"
    p.mkdir(parents=True,exist_ok=True)
    return p

def user_counts(user_id:int)->dict:
    conn=connect()
    result={
        "chats":conn.execute("SELECT COUNT(*) c FROM chats WHERE user_id=?",(user_id,)).fetchone()["c"],
        "messages":conn.execute("""SELECT COUNT(*) c FROM chat_messages m
            JOIN chats c ON c.id=m.chat_id WHERE c.user_id=?""",(user_id,)).fetchone()["c"],
        "attachments":conn.execute("""SELECT COUNT(*) c FROM attachments a
            JOIN chats c ON c.id=a.chat_id WHERE c.user_id=?""",(user_id,)).fetchone()["c"],
    }
    conn.close()
    return result
