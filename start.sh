#!/bin/bash
set -e

export PORT=${PORT:-8000}
ROLE=${CELERY_WORKER:-0}  # 1 ise worker, aksi halde web

echo "[start.sh] PORT=$PORT ROLE=$ROLE"

if [ "$ROLE" = "1" ]; then
  echo "[start.sh] Starting Celery worker..."
  # Worker için migrate zorunlu değil; DB şeması web deploy'unda güncellenmiş olmalı.
  exec celery -A marifetli_project worker -l info
else
  echo "[start.sh] Running migrate..."
  python manage.py migrate --noinput
  echo "[start.sh] Migrate OK, starting gunicorn (healthcheck will hit /)..."
  exec gunicorn marifetli_project.wsgi:application --bind "0.0.0.0:$PORT" --workers 3 --timeout 120
fi
