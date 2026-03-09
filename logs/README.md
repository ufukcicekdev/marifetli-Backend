# Logs uygulaması

Uygulama loglarını veritabanında saklar. Özellikle **moderation** ve **cronjobs** (Celery) logları DB'ye yazılır.

## Modeller

- **LogEntry**
  - `created_at` – kayıt zamanı
  - `level` – DEBUG, INFO, WARNING, ERROR, CRITICAL
  - `logger_name` – örn. `moderation.services`, `cronjobs.tasks`
  - `message` – log mesajı (en fazla 10000 karakter)
  - `source` – filtre için (moderation, cronjobs vb.)
  - `extra` – JSON, ek alanlar

## Ayarlar (.env)

- **LOG_TO_DB** – `True` (varsayılan): moderation ve cronjobs logları DB'ye yazılır. `False` ile kapatılır.
- **LOG_DIR** – doluysa aynı loglar dosyaya da gider (`logs/django.log`).

## Admin

Django Admin → **Uygulama Logları** → **Log kayıtları**: tarih, seviye, logger, mesaj, source ile listeleme ve arama.

## Migration

```bash
cd marifetli/backend
python manage.py migrate logs
```

## Hangi loglar DB'ye gider?

Sadece `moderation` ve `cronjobs` logger'larından gelen kayıtlar (INFO ve üzeri). Root logger veya diğer uygulamalar DB'ye yazılmaz; sadece konsol/dosyaya gider.
