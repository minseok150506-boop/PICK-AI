import argparse, shutil, sqlite3
from pathlib import Path
from config import DB_PATH
def check(path):
    c=sqlite3.connect(str(path)); r=c.execute("PRAGMA integrity_check").fetchone()[0]; c.close()
    if r!="ok": raise RuntimeError(r)
def main():
    p=argparse.ArgumentParser(); p.add_argument("backup"); p.add_argument("--force",action="store_true"); a=p.parse_args()
    b=Path(a.backup).resolve()
    if not b.exists(): raise SystemExit("백업 파일이 없습니다.")
    check(b)
    if DB_PATH.exists() and not a.force: raise SystemExit("현재 DB가 있습니다. --force를 추가하세요.")
    if DB_PATH.exists(): shutil.copy2(DB_PATH,DB_PATH.with_suffix(".before_restore.db"))
    shutil.copy2(b,DB_PATH); check(DB_PATH); print("복원 완료:",DB_PATH)
if __name__=="__main__": main()
