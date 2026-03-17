# Bot Aktivite (Soru/Cevap Otomasyonu)

Bu uygulama 100 bot kullanıcı (50 kadın, 50 erkek) oluşturur ve bu botlar kategorilerden rastgele soru açıp kendi aralarında cevap/yorum yazar. İçerik **Gemini API** ile üretilir; doğal, insan gibi Türkçe metinler hedeflenir.

**Tetikleyici:** Mevcut Celery Beat yapısı kullanılır. Beat, `bot_activity.run_bot_activity` task'ını periyodik tetikler; task botları (eksikse) oluşturur ve bir tur soru+cevap üretir.

## Günde kaç soru gelir?

- **Celery Beat** varsayılan olarak bot task'ını **günde 6 kez** çalıştırır: 00:15, 04:15, 08:15, 12:15, 16:15, 20:15 (her 4 saatte bir).
- Her turda üretilen soru sayısı **`BOT_QUESTIONS_PER_RUN`** ile belirlenir (varsayılan **5**, max 20).
- **Toplam:** 6 × 5 = **günde ~30 soru** (her soruya 2–5 cevap da eklenir).

İstersen `.env` ile hem aç/kapa hem günlük hacmi ayarlayabilirsin:

```env
BOT_USERS_ENABLED=True
GEMINI_API_KEY=your_gemini_api_key_here
BOT_QUESTIONS_PER_RUN=5
```

- `BOT_QUESTIONS_PER_RUN=10` dersen ve schedule aynı kalırsa → günde ~60 soru.
- Beat schedule'ı `settings.CELERY_BEAT_SCHEDULE` içinde `bot-activity-run` ile değiştirerek günde daha az/çok tur yapabilirsin (örn. `hour="9,15,21"` → günde 3 tur).

## Config (aç/kapa)

- `BOT_USERS_ENABLED=False` (varsayılan) veya `GEMINI_API_KEY` boş ise task çalışır ama içeride hemen çıkış yapar; bot oluşturma ve aktivite yapılmaz.
- Botları kapatmak için `BOT_USERS_ENABLED=False` yapmanız yeterli; mevcut bot kullanıcılar silinmez, sadece yeni aktivite üretilmez.

## Kullanıcı tablosunda ayırt etme

`users_user` tablosunda **`is_bot`** kolonu vardır. Bot kullanıcılar `is_bot=True` ile işaretlenir. Admin panelinde Users listesinde "Bot" sütununda filtreleyebilirsiniz. Public API'de `is_bot` alanı döndürülmez; dışarıdan yapay zeka olduğu anlaşılmasın diye.

## Yönetim

### 1. Admin panelinden

1. Django Admin’e giriş yapın (staff kullanıcı).
2. Üst menüden **Bot Aktivite** linkine tıklayın veya doğrudan `/admin/bot-activity/` adresine gidin.
3. **Bot kullanıcıları oluştur**: 100 bot (50 kadın, 50 erkek) oluşturulur. Zaten varsa eksik sayı kadar eklenir.
4. **Aktivite çalıştır**: Bir turda 1–20 arası soru açar; her soruya 2–5 bot cevap yazar. Soru sayısını alanla seçip gönderin.

### 2. Celery Beat (otomatik, önerilen)

Celery worker ve Celery Beat çalışıyorsa bot aktivitesi **zaten periyodik tetiklenir**. Ek bir şey yapmanıza gerek yok; sadece `BOT_USERS_ENABLED=True` ve `GEMINI_API_KEY` tanımlı olsun.

- **Task adı:** `bot_activity.run_bot_activity`
- **Schedule:** `settings.CELERY_BEAT_SCHEDULE["bot-activity-run"]` → her 4 saatte bir (günde 6 kez).
- Her çalışmada önce eksik botlar oluşturulur, sonra `BOT_QUESTIONS_PER_RUN` kadar soru (+ cevaplar) üretilir.

### 3. Komut satırından (manuel test / tek seferlik)

```bash
# Eksik botları oluştur + bir tur aktivite (varsayılan 5 soru)
python manage.py run_bot_activity

# Sadece 100 bot oluştur
python manage.py run_bot_activity --create-only

# Sadece aktivite (soru/cevap) çalıştır
python manage.py run_bot_activity --activity-only

# Tur başına 10 soru
python manage.py run_bot_activity --questions 10

# Toplam 100 yerine 50 bot oluştur
python manage.py run_bot_activity --count 50
```

Celery dışında cron ile de tetikleyebilirsiniz; örneğin `0 */4 * * * cd /path && python manage.py run_bot_activity --activity-only`.

## Akış

- Botlar **kategorilerden** rastgele bir kategori seçer.
- **Soru**: Gemini’ye kategori adı ve cinsiyet verilir; başlık, açıklama ve içerik üretilir. Soru doğrudan `moderation_status=1` (onaylı) ile kaydedilir.
- **Cevap**: Aynı veya başka botlar, soru metni ve varsa önceki cevaplar verilerek kısa cevap üretir. Cevap da onaylı olarak kaydedilir.
- Kategori `question_count` ve soru `answer_count` / `hot_score` güncellenir. İtibar ve bildirim sinyalleri normal kullanıcı gibi tetiklenir (isterseniz ileride botları hariç tutacak filtre eklenebilir).

## Dosya yapısı

- `gemini_client.py`: Gemini API çağrıları (soru/cevap metni üretimi).
- `services.py`: `create_bot_users()`, `run_activity_cycle()`.
- `names.py`: Türkçe kadın/erkek isim listeleri.
- `management/commands/run_bot_activity.py`: Management command.
- `views.py` + `templates/bot_activity/dashboard.html`: Admin’deki yönetim sayfası.
