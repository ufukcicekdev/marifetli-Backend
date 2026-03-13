# Google Search Console — Sitemap API ile gönderim

Sitemap URL'leri **ping (Google/Bing) ile değil**, doğrudan **Google Search Console API** ile property'ye submit edilir. Bing kullanılmaz.

## 1. GSC’de sitemap’i bir kez manuel ekleme

API ile submit etmeden önce property’yi kurman gerekir:

1. [Google Search Console](https://search.google.com/search-console) → Siteni seç (URL-prefix: `https://www.marifetli.com.tr/`).
2. Sol menü → **Sitemaps** (Site haritası).
3. “Yeni site haritası ekle” alanına **`sitemap.xml`** yaz → **Gönder**.

Bundan sonra API ile yapılan submit’ler bu property’ye gider.

---

## 2. API kimlik bilgisi (token) alma

Search Console API’ye istek atabilmek için **Google Cloud’da Service Account** oluşturup GSC property’ye kullanıcı eklemen gerekir.

### Adımlar

1. **Google Cloud Console**  
   [console.cloud.google.com](https://console.cloud.google.com) → Proje seç (veya yeni proje).

2. **Search Console API’yi aç**  
   “API’ler ve Hizmetler” → “Kütüphane” → “Google Search Console API” ara → **Etkinleştir**.

3. **Service Account oluştur**  
   “API’ler ve Hizmetler” → “Kimlik Bilgileri” → “Kimlik Bilgileri oluştur” → “Hizmet hesabı”.  
   İsim ver (örn. `gsc-sitemap`), “Oluştur ve devam et” → Rol verme isteğe bağlı → “Bitti”.

4. **Anahtar (JSON) oluştur**  
   Oluşan hizmet hesabına tıkla → “Anahtarlar” → “Anahtar ekle” → “Yeni anahtar” → **JSON** → İndir.  
   Bu dosyayı güvenli yerde sakla (repo’ya koyma).

5. **GSC property’ye kullanıcı ekle**  
   [Search Console](https://search.google.com/search-console) → Siteni seç → **Ayarlar** → “Kullanıcılar ve izinler” → “Kullanıcı ekle”.  
   Service Account’un **e-posta adresini** (örn. `gsc-sitemap@proje-id.iam.gserviceaccount.com`) ekle → **Sınırlı** veya **Tam** erişim ver → Kaydet.

---

## 3. Backend’e kimlik bilgisi verme

İki yol:

### A) JSON dosyası

- İndirdiğin JSON dosyasının yolunu `.env`’e yaz:
  - `SEARCH_CONSOLE_CREDENTIALS_PATH=/path/to/gsc-service-account.json`  
  veya
  - `GOOGLE_APPLICATION_CREDENTIALS=/path/to/gsc-service-account.json`

### B) .env’de tek tek (dosya kullanmadan)

JSON’daki alanları `.env`’e yaz (Firebase gibi):

```env
GSC_PROJECT_ID=proje-id
GSC_CLIENT_EMAIL=gsc-sitemap@proje-id.iam.gserviceaccount.com
GSC_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

`GSC_PRIVATE_KEY`: JSON’daki `private_key` değerini tek satırda, satır sonları `\n` olacak şekilde yapıştır. Tırnak içinde ver.

---

## 4. Site URL’si

Sitemap’lerin tam URL’leri `SEARCH_CONSOLE_SITE_URL` ile üretilir (sitemap’lerin yayında olduğu site).

`.env` örneği:

```env
SEARCH_CONSOLE_SITE_URL=https://www.marifetli.com.tr
```

Bu URL, GSC’deki property URL’si ile aynı olmalı (örn. `https://www.marifetli.com.tr/`).

---

## 5. Otomatik gönderim (Celery Beat)

Celery Beat zamanlaması günde 3 kez (08:00, 14:00, 20:00 – Europe/Istanbul) **sitemap’leri GSC API ile submit** eder. Ping gönderilmez.

- Task adı: `search_console.submit_sitemaps_gsc`
- Beat’in çalışması gerekir (örn. `celery -A marifetli_project worker -l info -B` veya ayrı beat process).

---

## 6. Manuel test

```bash
cd backend
python manage.py submit_sitemaps_gsc
```

Sadece hangi URL’lerin gönderileceğini görmek için:

```bash
python manage.py submit_sitemaps_gsc --dry-run
```

Sitemap URL listesi:

```bash
python manage.py list_sitemap_urls
```

---

## 403 Forbidden — "User does not have sufficient permission"

Bu hata, **Service Account e-postasının** Search Console property’sine kullanıcı olarak eklenmediği anlamına gelir.

**Yapman gereken:**

1. [Google Search Console](https://search.google.com/search-console) → **https://www.marifetli.com.tr/** property’sini seç.
2. Sol menüden **Ayarlar** (dişli) → **Kullanıcılar ve izinler**.
3. **Kullanıcı ekle** → `.env` içindeki **`GSC_CLIENT_EMAIL`** değerini (örn. `xxx@proje-id.iam.gserviceaccount.com`) yapıştır.
4. İzin: **Sınırlı** veya **Tam** → **Ekle**.

Birkaç dakika sonra `python manage.py submit_sitemaps_gsc` komutunu tekrar dene.

---

## Özet

| Ne | Nasıl |
|----|--------|
| Sitemap GSC’de görünsün | Search Console → Sitemaps → `sitemap.xml` ekle. |
| API ile gönderim | Service Account + GSC’de kullanıcı + `GSC_*` veya `SEARCH_CONSOLE_CREDENTIALS_PATH`. |
| Günde 3 kez otomatik | Celery Beat çalışsın (`submit_sitemaps_gsc` task’ı). |
| Bing / ping | Kullanılmıyor; sadece Google Search Console API. |
