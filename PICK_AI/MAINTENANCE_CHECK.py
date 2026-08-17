import sqlite3
from config import DB_PATH
from database import init_db
from memory_store import init_memory_schema
def main():
    init_db(); init_memory_schema()
    c=sqlite3.connect(str(DB_PATH)); integrity=c.execute("PRAGMA integrity_check").fetchone()[0]; fk=c.execute("PRAGMA foreign_key_check").fetchall(); c.execute("PRAGMA optimize"); c.close()
    print("DB integrity:",integrity); print("Foreign key errors:",len(fk))
    if integrity!="ok" or fk: raise SystemExit(1)
if __name__=="__main__": main()
