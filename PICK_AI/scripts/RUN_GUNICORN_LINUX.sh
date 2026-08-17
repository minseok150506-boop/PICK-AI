#!/bin/sh
export PICK_SECRET_KEY=${PICK_SECRET_KEY:-pick-service-secret}
gunicorn app:app -b 0.0.0.0:5000
