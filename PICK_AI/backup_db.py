import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, DB_PATH


def main():
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"pick_service_{datetime.now():%Y%m%d_%H%M%S}.db"

    source = sqlite3.connect(str(DB_PATH))
    dest = sqlite3.connect(str(target))
    with dest:
        source.backup(dest)
    source.close()
    dest.close()

    # Keep newest 14 backups.
    files = sorted(backup_dir.glob("pick_service_*.db"), reverse=True)
    for old in files[14:]:
        old.unlink(missing_ok=True)

    print(target)


if __name__ == "__main__":
    main()
