#!/bin/bash
set -e
export PORT=${PORT:-8000}
# Migrate önce; bittikten sonra gunicorn başlar (healthcheck bu sıraya göre çalışır)
python manage.py migrate --noinput
exec gunicorn marifetli_project.wsgi:application --bind "0.0.0.0:$PORT" --workers 3
