# Search Console & Sitemap Ping

## 1. Sitemap’i Search Console’da görmek

**Ping** sadece Google/Bing’e “sitemap güncellendi, tekrar tara” der; sitemap’i Search Console arayüzüne **eklemez**.

Sitemap’in GSC’de listelenmesi için **bir kez manuel eklemen** gerekir:

1. [Google Search Console](https://search.google.com/search-console) → Siteni seç.
2. Sol menüden **Sitemaps** (Site haritası) aç.
3. “Yeni site haritası ekle” alanına **`sitemap.xml`** yaz (veya tam URL: `https://www.marifetli.com.tr/sitemap.xml`).
4. **Gönder**’e tıkla.

Bundan sonra GSC sitemap’i listeler ve ping’ler güncellemeyi tetikler.

---

## 2. Günde 3 kez ping (Celery Beat)

Ping’in günde 3 kez (08:00, 14:00, 20:00 – Europe/Istanbul) otomatik çalışması için **Celery Beat**’in ayakta olması gerekir. Sadece worker çalışıyorsa zamanlanmış görev tetiklenmez.

### Yerelde

İki ayrı terminalde:

```bash
# Terminal 1: Worker (görevleri işler)
celery -A marifetli_project worker -l info

# Terminal 2: Beat (zamanlanmış görevi tetikler)
celery -A marifetli_project beat -l info
```

Tek komutla (worker + beat birlikte):

```bash
celery -A marifetli_project worker -l info -B
```

### Canlıda (Railway / Render / vb.)

- **Worker** için bir process: `celery -A marifetli_project worker -l info`
- **Beat** için ayrı bir process: `celery -A marifetli_project beat -l info`

Beat’i ayrı bir servis/process olarak tanımlamazsan `ping-sitemaps` zamanlaması hiç çalışmaz.

---

## 3. Manuel test

Ping’i hemen denemek için:

```bash
cd backend
python manage.py ping_sitemaps
```

Sitemap URL’lerini görmek için:

```bash
python manage.py list_sitemap_urls
```

---

## Özet

| Ne | Nasıl |
|----|--------|
| Sitemap GSC’de görünsün | Search Console → Sitemaps → “sitemap.xml” ekle, Gönder. |
| Ping günde 3 kez gitsin | Celery **Beat** process’ini çalıştır (worker’dan ayrı veya `-B` ile). |
| Ping 404/410 alıyorsa | Sitemap'lar backend'de de sunuluyor. Domain backend'e yönleniyorsa deploy sonrası düzelir. |
