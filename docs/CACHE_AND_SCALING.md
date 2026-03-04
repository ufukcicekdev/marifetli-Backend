# Ölçeklenebilirlik ve Cache Yönetimi

Kullanıcı ve içerik arttıkça yükü azaltmak için yapılanlar ve ileride alınabilecek önlemler.

## 1. Şu an yapılanlar

### Cache (Redis / LocMem)
- **Soru listesi** (`/api/questions/`): GET yanıtları cache’leniyor (sayfa, sıra, arama, filtreye göre key).
- **TTL**: Varsayılan 60 saniye (`.env`: `CACHE_TTL_QUESTION_LIST=60`).
- **Invalidation**: Yeni soru eklenince, soru güncellenince veya silinince liste cache versiyonu artırılıyor; bir sonraki istekler yeni veriyi alıyor.
- **Backend**: Redis yoksa `LocMemCache` (tek sunucu), Redis varsa tüm instance’lar aynı cache’i kullanır.

### Veritabanı sorguları
- Soru listesi: `select_related('author', 'category')` ve `prefetch_related('tags')` ile N+1 azaltıldı.
- Soru detay: Aynı şekilde `select_related` / `prefetch_related` kullanılıyor.

### Pagination
- DRF `PageNumberPagination`, sayfa başına 20 kayıt (`PAGE_SIZE=20`). Liste API’leri sayfalı.

---

## 2. Redis’i açmak

Production’da Redis kullanmak için `.env`:

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

Railway / Upstash / Redis Cloud gibi servislerden alacağın URL’i aynı şekilde `REDIS_URL` olarak ver. Redis yoksa uygulama `LocMemCache` ile çalışmaya devam eder.

---

## 3. İleride eklenebilecekler

### Backend
- **Soru detay cache**: Çok okunan sorularda `get_question_detail_cache_key(slug)` ile 30–60 sn cache (şu an sadece key helper var, view’a bağlanmadı).
- **Rate limiting**: DRF throttle veya `django-ratelimit` ile API isteklerini sınırlama.
- **DB index**: `Question(status, created_at)`, `Question(hot_score)`, `Answer(question_id, created_at)` gibi sık filtre/sıralama alanlarına index.
- **Read replica**: Okuma trafiği çok artarsa PostgreSQL read replica’a okuma yönlendirme.

### Frontend
- **React Query**: `staleTime` / `gcTime` ile liste sayfalarında gereksiz refetch azaltma.
- **ISR / SSG**: Next.js’te soru listesi veya popüler sayfalar için incremental static regeneration.

### Altyapı
- **CDN**: Statik dosyalar ve (mümkünse) bazı API yanıtları için CDN.
- **Görsel optimizasyonu**: Thumbnail, WebP, lazy load (zaten yapılıyor olabilir).

---

## 4. Cache key’leri (referans)

| Amaç              | Key örneği / helper                          | TTL (config)        |
|-------------------|----------------------------------------------|---------------------|
| Soru listesi      | `core.cache_utils.get_question_list_cache_key(request)` | `CACHE_TTL_QUESTION_LIST` (60 sn) |
| Liste invalidation| `core.cache_utils.invalidate_question_list()` | -                   |

Yeni bir liste/detay cache’i eklersen `core/cache_utils.py` içine key ve (isteğe bağlı) invalidation fonksiyonu ekleyip bu dokümana not düşmek yeterli.
