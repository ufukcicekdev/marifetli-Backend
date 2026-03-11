# Search Console / Sitemap Indexleme

Yeni sorular, blog yazıları ve sayfaların Google (ve Bing) tarafından daha hızlı indexlenmesi için sitemap ping ve isteğe bağlı Search Console API entegrasyonu.

## 1. Sitemap ping (önerilen, API anahtarı gerekmez)

Google ve Bing’e “sitemap güncellendi” bildirimi gönderir. Arama motorları sitemap’i tekrar tarayıp yeni URL’leri keşfeder.

### Komut

```bash
python manage.py ping_sitemaps
```

### Ne yapılır?

- `SEARCH_CONSOLE_SITE_URL` (veya `FRONTEND_URL`) ile sitemap tam URL’leri oluşturulur.
- Varsayılan sitemap’ler: `sitemap.xml`, `sitemap-static.xml`, `sitemap-questions.xml`, `sitemap-blog.xml`
- Her biri için `https://www.google.com/ping?sitemap=...` ve `https://www.bing.com/ping?sitemap=...` çağrılır.

### Günde 3 kez otomatik (Celery Beat)

Projede Celery Beat açıksa sitemap ping **zaten periyodik çalışır** (settings’te `CELERY_BEAT_SCHEDULE`): 08:00, 14:00, 20:00 (Europe/Istanbul).

Celery worker + beat’i şöyle başlatın:

```bash
# Worker
celery -A marifetli_project worker -l info

# Beat (ayrı process veya aynı makinede)
celery -A marifetli_project beat -l info
```

İsterseniz tek seferlik manuel çalıştırma:

```bash
python manage.py ping_sitemaps
```

Cron kullanacaksanız (Beat yoksa):

```cron
0 8,14,20 * * * cd /path/to/backend && python manage.py ping_sitemaps
```

### Ayarlar (.env)

| Değişken | Açıklama |
|----------|----------|
| `SEARCH_CONSOLE_SITE_URL` | Sitemap’lerin sunulduğu site (örn. `https://www.marifetli.com.tr`). Boşsa `FRONTEND_URL` kullanılır. |

---

## 2. Google Search Console API (opsiyonel)

Sitemap’leri GSC property’ye programatik olarak submit etmek için (ilk kurulum veya sitemap listesini API ile güncellemek isterseniz).

### Gereksinimler

1. **Google Cloud Console**
   - Proje oluştur
   - “Google Search Console API” etkinleştir
   - Service account oluştur, JSON anahtar indir

2. **Google Search Console**
   - Site property’sine (URL-prefix) service account e-posta adresini “Kullanıcı” olarak ekle

3. **Backend**
   - `pip install google-api-python-client google-auth`
   - JSON dosya yolunu ayarla (aşağıda)

### Komut

```bash
python manage.py submit_sitemaps_gsc
```

### Ayarlar

| Ayar | Açıklama |
|------|----------|
| `SEARCH_CONSOLE_CREDENTIALS_PATH` veya `GOOGLE_APPLICATION_CREDENTIALS` | Service account JSON dosyasının yolu |

---

## Özet

- **Sadece indexleme hızı** için: `ping_sitemaps` yeterli; günde 2–3 kez cron ile çalıştırın.
- **GSC’de sitemap listesini API ile yönetmek** isterseniz: `submit_sitemaps_gsc` ve service account kurulumu kullanın.
