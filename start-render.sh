#!/bin/sh
set -e

if [ -d "/data" ]; then
  mkdir -p /data/output/videos /data/output/audio /data/output/scenes
  mkdir -p /data/memory /data/assets/music /data/assets/characters

  rm -rf /app/output
  ln -s /data/output /app/output

  rm -f /app/memory/agent_memory.db
  ln -s /data/memory/agent_memory.db /app/memory/agent_memory.db

  rm -rf /app/assets/music /app/assets/characters
  ln -s /data/assets/music /app/assets/music
  ln -s /data/assets/characters /app/assets/characters

  # Persist client API-key settings across restarts/redeploys
  mkdir -p /data/config
  rm -f /app/config/client_settings.json
  ln -s /data/config/client_settings.json /app/config/client_settings.json
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
