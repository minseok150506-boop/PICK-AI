#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r requirements.txt
python -c "from database import init_db; init_db(); print('database initialized')"
