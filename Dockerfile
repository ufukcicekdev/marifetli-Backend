FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files (run during build for production)
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

# Railway sets PORT; fallback to 8000 for local Docker
CMD gunicorn marifetli_project.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
