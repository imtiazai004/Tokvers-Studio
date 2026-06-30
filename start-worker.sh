#!/bin/sh
# New Tokverse Studio background worker — runs the generation pipeline
# (script -> voice -> video -> ffmpeg edit -> R2 upload) off the web process.
set -e

exec python -m arq worker.WorkerSettings
