#!/bin/bash
set -e

export PORT=${PORT:-8000}
ROLE=${CELERY_WORKER:-0}  # 1 ise worker, aksi halde web

echo "[start.sh] PORT=$PORT ROLE=$ROLE"

if [ "$ROLE" = "1" ]; then
  echo "[start.sh] Starting healthcheck HTTP server + Celery worker..."
  # Sadece healthcheck için çok hafif HTTP server (PORT üzerinde 200 döner)
  python -m http.server "$PORT" &
  # Worker + Beat (günde 3 kez sitemap ping vb. zamanlanmış görevler için -B)
  exec celery -A marifetli_project worker -l info -B
  
else
  echo "[start.sh] Running migrate..."
  python manage.py migrate --noinput
  echo "[start.sh] Migrate OK, starting daphne ASGI (HTTP + WebSocket)..."
  exec daphne -b 0.0.0.0 -p "$PORT" --http-timeout 180 marifetli_project.asgi:application
fi
