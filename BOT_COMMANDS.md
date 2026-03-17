# Bot aktivite — komutlar ve parametreler

## Yapman gerekenler (özet)

1. **.env** — `BOT_USERS_ENABLED=True` ve `GEMINI_API_KEY=...` doldur.
2. **Celery Worker + Beat** — Aynı projede zaten çalışıyorsa ekstra bir şey yok. Beat, bot task'ını günde 6 kez tetikler.
3. **İlk çalışmada:** Task tetiklenince önce 100 bot kullanıcı (yoksa/eksikse) oluşturulur, ardından o turda `BOT_QUESTIONS_PER_RUN` kadar soru + cevap üretilir. Yani Celery çalıştığında kullanıcılar ve sorular otomatik gelir.

Botları kapatmak için `.env` içinde `BOT_USERS_ENABLED=False` yapman yeterli.

---

## .env parametreleri

```env
# Aç/kapa (True = botlar çalışır)
BOT_USERS_ENABLED=False

# Gemini API anahtarı (Google AI Studio’dan alınır)
GEMINI_API_KEY=

# Her Celery turunda kaç soru üretilsin (1–20). Günde ~6 tur → 6 × bu değer soru.
BOT_QUESTIONS_PER_RUN=5
```

---

## Django management komutu

Backend dizininde (`marifetli/backend`):

```bash
# Botları tamamla + bir tur aktivite (varsayılan 5 soru)
python manage.py run_bot_activity

# Sadece 100 bot kullanıcı oluştur
python manage.py run_bot_activity --create-only

# Sadece aktivite çalıştır (soru + cevap), bot oluşturma
python manage.py run_bot_activity --activity-only

# Bu turda 10 soru üret
python manage.py run_bot_activity --questions 10

# Toplam 50 bot oluştur (varsayılan 100)
python manage.py run_bot_activity --count 50
```

**Seçenekler:**

| Seçenek           | Açıklama                              | Varsayılan |
|-------------------|----------------------------------------|------------|
| `--create-only`   | Sadece bot kullanıcıları oluştur       | -          |
| `--activity-only` | Sadece soru/cevap turu çalıştır        | -          |
| `--questions N`   | Tur başına soru sayısı (1–20)         | 5          |
| `--count N`       | Oluşturulacak toplam bot sayısı       | 100        |

---

## Celery

**Task adı:** `bot_activity.run_bot_activity`

**Ne yapar:** Eksik botları tamamlar (100’e kadar), sonra `BOT_QUESTIONS_PER_RUN` kadar soru + cevap üretir. `BOT_USERS_ENABLED=False` veya `GEMINI_API_KEY` boşsa hiçbir işlem yapmadan çıkar.

**Beat schedule (varsayılan):** Günde 6 kez — 00:15, 04:15, 08:15, 12:15, 16:15, 20:15 (her 4 saatte bir).  
Tanım: `settings.CELERY_BEAT_SCHEDULE["bot-activity-run"]`.

**Manuel tetikleme (Python shell veya script):**

```python
from bot_activity.tasks import run_bot_activity_task
run_bot_activity_task.delay()
```

---

## Admin paneli

- **URL:** `/admin/bot-activity/`
- **Erişim:** Sadece staff kullanıcılar.
- **İçerik:** Bot sayısı, “Bot kullanıcıları oluştur” butonu, “Aktivite çalıştır” (soru sayısı seçilebilir).

Jazzmin üst menüde **Bot Aktivite** linki de bu sayfaya gider.

---

## Cron ile tetikleme (Celery kullanmıyorsan)

Örnek: Her 4 saatte bir sadece aktivite turu:

```cron
0 */4 * * * cd /path/to/marifetli/backend && python manage.py run_bot_activity --activity-only
```

---

## Özet

| Yöntem              | Ne zaman kullanılır                          |
|---------------------|----------------------------------------------|
| Celery Beat         | Otomatik, sürekli bot aktivitesi (önerilen)  |
| `run_bot_activity`  | Manuel test veya tek seferlik tur            |
| Admin /admin/bot-activity/ | Tarayıcıdan bot oluşturma / tek tur çalıştırma |
| Cron                | Celery yoksa periyodik tetikleme            |
