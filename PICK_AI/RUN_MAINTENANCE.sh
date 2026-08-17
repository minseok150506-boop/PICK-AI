#!/bin/sh
set -eu
docker exec pick-ai-web python /app/backup_db.py
docker exec pick-ai-web python /app/MAINTENANCE_CHECK.py
