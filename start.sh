#!/bin/bash
set -e
export PORT=${PORT:-8000}
echo "[start.sh] PORT=$PORT"
echo "[start.sh] Running migrate..."
python manage.py migrate --noinput
echo "[start.sh] Migrate OK, starting gunicorn..."
exec gunicorn marifetli_project.wsgi:application --bind "0.0.0.0:$PORT" --workers 3
