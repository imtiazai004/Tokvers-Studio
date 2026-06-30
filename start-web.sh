#!/bin/sh
# New Tokverse Studio web service (multi-tenant app/main.py).
# Applies DB migrations, then serves the API + frontend.
set -e

alembic upgrade head || echo "WARNING: migrations failed (continuing)"

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8001}"
