# Blog API – n8n ile yazı ekleme

Otomasyondan (n8n vb.) blog yazısı oluşturmak için tek endpoint kullanılır.

## Endpoint

- **URL:** `POST /api/blog/publish/`
- **Kimlik:** Header'da `X-API-Key: <BLOG_API_KEY>` (`.env` içinde tanımlı)

## .env ayarları

```env
# Zorunlu: n8n'de kullanacağın gizli anahtar
BLOG_API_KEY=your-secret-key-buraya

# Opsiyonel: Yazıların yazarı olacak kullanıcı adı. Boş bırakırsan ilk superuser kullanılır.
BLOG_AUTHOR_USERNAME=admin
```

## İstek gövdesi (JSON)

| Alan           | Zorunlu | Açıklama                                      |
|----------------|--------|-----------------------------------------------|
| `title`        | Evet   | Başlık (slug otomatik üretilir)               |
| `content`      | Evet   | İçerik (HTML veya düz metin)                  |
| `excerpt`      | Hayır  | Kısa özet (liste görünümünde, max 300 karakter) |
| `is_published` | Hayır  | `true` / `false` (varsayılan: `true`)         |

Örnek:

```json
{
  "title": "Örgüye Başlarken",
  "content": "<p>İlk adımda hangi malzemeleri almalısınız...</p>",
  "excerpt": "Yeni başlayanlar için örgü rehberi.",
  "is_published": true
}
```

## n8n kullanımı

1. **HTTP Request** node ekle.
2. **Method:** POST  
3. **URL:** `https://your-backend.com/api/blog/publish/` (veya local: `http://localhost:8000/api/blog/publish/`)
4. **Authentication:** None (veya “Header Auth” kullanacaksan aşağıdaki gibi header ekle).
5. **Headers:**
   - `Content-Type`: `application/json`
   - `X-API-Key`: `your-secret-key-buraya` (veya n8n Credentials’tan)
6. **Body (JSON):** Yukarıdaki örnek gibi `title`, `content`, isteğe `excerpt` ve `is_published`.

Başarılı yanıt: **201 Created**, gövdede oluşturulan blog yazısı (id, slug, title, content, published_at vb.) döner.

Hatalar:
- **401:** `X-API-Key` yok veya yanlış.
- **400:** `title` veya `content` eksik / validasyon hatası.
- **503:** Yazar kullanıcı bulunamadı (BLOG_AUTHOR_USERNAME veya superuser gerekli).

---

## Celery ile konu tablosundan otomatik blog

n8n yerine doğrudan backend içinde otomasyon çalıştırmak için:

```env
BLOG_AUTOMATION_ENABLED=true
GEMINI_API_KEY=your-gemini-key
BLOG_AUTHOR_USERNAME=admin
```

- Admin panelde `Blog Topic Queue` tablosuna konu ekleyin (`topic` alanı).
- Celery Beat görevi **2 günde bir** `blog.generate_blog_from_queue` task'ını çalıştırır.
- Task tamamlanmamış ilk satırı alır, yazıyı üretir/yayımlar, satırı `is_completed=true` yapar.
- Hata olursa `last_error` alanına yazar; satır tamamlanmaz, sonraki turda tekrar denenir.
