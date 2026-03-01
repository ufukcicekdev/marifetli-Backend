#!/bin/bash
set -e
export PORT=${PORT:-8000}
exec gunicorn marifetli_project.wsgi:application --bind "0.0.0.0:$PORT" --workers 3
