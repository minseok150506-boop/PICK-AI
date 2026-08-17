from __future__ import annotations
import importlib
import sqlite3
import sys
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parent
print('=== PICK AI DOCTOR ===')
print('Python:',sys.version.replace('\\n',' '))
print('Folder:',ROOT)

required=['flask','werkzeug','dotenv']
optional=['PIL','cv2','pypdf','docx','openpyxl','authlib','ntplib']
missing=[]
for name in required:
    try: importlib.import_module(name); print('[OK] required',name)
    except Exception as e: missing.append(name); print('[FAIL] required',name,':',e)
for name in optional:
    try: importlib.import_module(name); print('[OK] optional',name)
    except Exception as e: print('[WARN] optional',name,':',e)
if missing:
    print('\n필수 패키지가 없습니다. 먼저 START_PICK.bat을 실행하세요.')
    raise SystemExit(2)

try:
    import database
    database.init_db()
    c=database.connect()
    print('[OK] DB integrity:',c.execute('PRAGMA integrity_check').fetchone()[0])
    print('[OK] users columns:',','.join(r['name'] for r in c.execute('PRAGMA table_info(users)')))
    print('[OK] attachments columns:',','.join(r['name'] for r in c.execute('PRAGMA table_info(attachments)')))
    c.close()
except Exception:
    print('[FAIL] database')
    traceback.print_exc()
    raise SystemExit(3)

try:
    import app
    print('[OK] app import')
    client=app.app.test_client()
    r=client.get('/healthz')
    print('[OK] /healthz status:',r.status_code)
    r=client.get('/login')
    print('[OK] /login status:',r.status_code)
except Exception:
    print('[FAIL] app startup')
    traceback.print_exc()
    raise SystemExit(4)

print('\nPICK 기본 실행 검사 통과')
