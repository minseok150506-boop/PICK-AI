#!/bin/sh
export PICK_SECRET_KEY=${PICK_SECRET_KEY:-change-this-secret}
export PICK_LLM_MODE=${PICK_LLM_MODE:-local}
gunicorn app:app -b 0.0.0.0:5000
