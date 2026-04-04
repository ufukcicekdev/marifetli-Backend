# Kategori uzmanı (AI)

Ana kategorilere bağlı “uzman” asistan: kullanıcı sorar, yanıt LLM ile üretilir; tüm soru–cevaplar `CategoryExpertQuery` tablosunda saklanır.

## .env

```env
# Özelliği aç/kapa
CATEGORY_EXPERT_ENABLED=False

# LLM: moderator_chat (varsayılan, Marifetli moderator /chat) | gemini | stub | myapp.providers.MyProvider
CATEGORY_EXPERT_LLM_PROVIDER=moderator_chat

# Moderasyon ile aynı moderator servisi (uzman /chat bununla türetilir)
MODERATION_LLM_URL=https://ornek.railway.app/moderate

# Chat URL: boş bırakılırsa MODERATION_LLM_URL ile aynı sunucuda /moderate veya /moderator → /chat türetilir.
# Sadece farklı bir adres kullanacaksan:
# CATEGORY_EXPERT_CHAT_URL=https://...
CATEGORY_EXPERT_CHAT_TIMEOUT=120
# İsteğe bağlı: servis Bearer istiyorsa
# CATEGORY_EXPERT_CHAT_BEARER_TOKEN=

# Kullanıcı başına soru limiti (0 = limitsiz)
CATEGORY_EXPERT_MAX_QUESTIONS_PER_USER=3

# Limit penceresi: day (varsayılan) | month | all_time
CATEGORY_EXPERT_LIMIT_PERIOD=day
# Eski all_time env'i kaldırmadan günlük limit istiyorsanız varsayılan yeterli.
# Gerçekten ömür boyu toplam limit için:
# CATEGORY_EXPERT_LIMIT_PERIOD=all_time
# CATEGORY_EXPERT_ALLOW_LIFETIME_EXPERT_LIMIT=True

# Sadece CATEGORY_EXPERT_LLM_PROVIDER=gemini ise gerekli (bot ile aynı anahtar)
# GEMINI_API_KEY=
# GEMINI_MODEL=gemini-2.0-flash
```

## Kurulum

```bash
python manage.py migrate
python manage.py seed_category_experts   # Tüm ana kategorilere CategoryExpert kaydı
python manage.py seed_kids_expert_categories  # Kids odaklı uzman kategorileri + alt başlıklar
```

Admin: **Kategori uzmanları** — yeni ana kategori ekledikten sonra uzman kaydı oluşturun veya `seed_category_experts` tekrar çalıştırın. Pasif (`is_active=False`) uzmanlar API listesinde dönmez.

## API

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/api/category-experts/` | Herkese açık: `enabled`, `backend_ready`, kategoriler, girişliyse `remaining_questions` |
| POST | `/api/category-experts/ask/` | JWT + doğrulanmış e-posta: JSON `{ main_category_id, subcategory_id?, question }` veya `multipart/form-data` ile aynı alanlar + isteğe bağlı `attachment` (JPEG/PNG/WebP/GIF, max 5MB). Görsel varsa soru metni 1+ karakter yeterli. |
| GET | `/api/category-experts/my-history/` | Son 50 soru–cevap |

## Görsel eki gerçekten modele gidiyor mu?

- **Frontend:** `multipart/form-data` ile `attachment` alanında dosya gönderilir (`api.askCategoryExpert`).
- **Django:** Dosya okunur; MIME önce **dosya imzası (magic bytes)**, sonra `Content-Type` / dosya adı ile belirlenir. `generate_answer(..., attachment_bytes=..., attachment_mime=..., attachment_name=...)` çağrılır.
- **`CATEGORY_EXPERT_LLM_PROVIDER=gemini`:** Görsel doğrudan Gemini’ye multimodal olarak gider.
- **`CATEGORY_EXPERT_LLM_PROVIDER=moderator_chat`:** Harici `/chat` uç noktasına **JSON** gider. Görsel varsa gövdeye şunlar eklenir (isimler birebir bu olmalı; servis farklı anahtar bekliyorsa görsel yok sayılır ve model sadece metne bakar):
  - `message` (string, tam sistem + kullanıcı metni)
  - `attachment_base64` (standart Base64, satır sonu yok)
  - `attachment_mime_type` (örn. `image/jpeg`, `image/png`; parametre yok, küçük harf)
  - `attachment_name` (isteğe bağlı; yüklenen dosyanın güvenli `basename`’i — moderator servisiyle uyum)

Yanıt hâlâ “görseli görmemiş gibi” veya yanlış yorumluyorsa: Railway `/chat` kodunda Base64 + MIME’nin decode edilip modele **görüntü** olarak verildiğini doğrulayın; sadece `message` okunuyorsa analiz metin tabanlı kalır.

## Kendi modelinizi bağlamak

1. `category_experts/providers/` altında veya projenizde bir sınıf yazın:
   - `name: str`
   - `is_configured(self) -> bool`
   - `generate_answer(self, *, question, main_category_name, subcategory_name, expert_display_name, extra_instructions, attachment_bytes=None, attachment_mime=None, attachment_name=None) -> str`

2. `.env`: `CATEGORY_EXPERT_LLM_PROVIDER=mypackage.mymodule.MyExpertProvider`

## Frontend

- Tam sayfa: `/uzman` (SEO + JSON-LD; statik sitemap’te `sitemap-static.xml` içinde listelenir).
- Sidebar / mega menü / anasayfa CTA: **Uzmana sor** → `/uzman`. Hızlı sohbet için sağdaki **FAB / panel** ayrı çalışır.
