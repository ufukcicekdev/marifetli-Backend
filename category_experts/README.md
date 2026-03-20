# Kategori uzmanı (AI)

Ana kategorilere bağlı “uzman” asistan: kullanıcı sorar, yanıt LLM ile üretilir; tüm soru–cevaplar `CategoryExpertQuery` tablosunda saklanır.

## .env

```env
# Özelliği aç/kapa
CATEGORY_EXPERT_ENABLED=False

# LLM: gemini (varsayılan) | stub (test) | myapp.providers.MyProvider
CATEGORY_EXPERT_LLM_PROVIDER=gemini

# Kullanıcı başına soru limiti (0 = limitsiz)
CATEGORY_EXPERT_MAX_QUESTIONS_PER_USER=3

# Limit penceresi: all_time | day | month
CATEGORY_EXPERT_LIMIT_PERIOD=all_time

# Gemini (gemini sağlayıcısı için; bot ile aynı anahtar)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
```

## Kurulum

```bash
python manage.py migrate
python manage.py seed_category_experts   # Tüm ana kategorilere CategoryExpert kaydı
```

Admin: **Kategori uzmanları** — yeni ana kategori ekledikten sonra uzman kaydı oluşturun veya `seed_category_experts` tekrar çalıştırın. Pasif (`is_active=False`) uzmanlar API listesinde dönmez.

## API

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/api/category-experts/` | Herkese açık: `enabled`, `backend_ready`, kategoriler, girişliyse `remaining_questions` |
| POST | `/api/category-experts/ask/` | JWT + doğrulanmış e-posta: `{ main_category_id, subcategory_id?, question }` |
| GET | `/api/category-experts/my-history/` | Son 50 soru–cevap |

## Kendi modelinizi bağlamak

1. `category_experts/providers/` altında veya projenizde bir sınıf yazın:
   - `name: str`
   - `is_configured(self) -> bool`
   - `generate_answer(self, *, question, main_category_name, subcategory_name, expert_display_name, extra_instructions) -> str`

2. `.env`: `CATEGORY_EXPERT_LLM_PROVIDER=mypackage.mymodule.MyExpertProvider`

## Frontend

- Sayfa: `/uzman`
- Menüde link yalnızca `enabled=true` iken görünür.
