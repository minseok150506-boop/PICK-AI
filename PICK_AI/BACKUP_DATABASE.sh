#!/bin/sh
set -eu
cd "$(dirname "$0")"
docker exec pick-ai-web python /app/backup_db.py
echo "PICK DB 백업 완료"
