# Moderation LLM servisi

Soru ve yorum gönderiminde metin önce **kötü kelime listesine** (DB: `moderation.BadWord`), ardından **LLM moderasyon servisine** gider.

## 1. Kötü kelime listesi (BadWord)

- Django Admin → Moderation → Kötü kelimeler.
- `word` (kelime), `is_active` (aktif mi).
- Liste cache’lenir (5 dk); ekleme/silme/güncellemede cache temizlenir.
- Metinde listedeki kelime **alt string** olarak geçiyorsa gönderi kabul edilmez, kullanıcıya uyarı döner.

## 2. LLM servisi (status + bad_words)

- Varsayılan URL: `https://marifetli-moderator-production.up.railway.app/moderate`
- **İstek:** `POST`, JSON body: `{"text": "kontrol edilecek metin"}` (en fazla 10000 karakter).
- **Cevap:** `{"status": "ONAY"}` veya `{"status": "RED", "bad_words": ["kelime1", "kelime2", ...]}`.
  - **ONAY:** İçerik kaydedilir.
  - **RED:** İçerik kaydedilmez, kullanıcıya bildirim gider; `bad_words` listesi **doğrudan BadWord’e eklenmez**, admin onayı için **SuggestedBadWord** tablosuna **pending** olarak yazılır (ör. "makrome" el işi adı olarak dönmüş olabilir, küfür değildir).

## 3. Önerilen kötü kelimeler (SuggestedBadWord)

- LLM’den dönen `bad_words` burada **beklemede** görünür.
- Admin → Moderation → Önerilen kötü kelimeler: listele, **Not** alanına açıklama yaz (isteğe bağlı).
- **Onayla:** Seçilen kayıtlar BadWord listesine eklenir, öneri "Onaylandı" olur.
- **Reddet:** Öneri "Reddedildi" olur (kelime BadWord’e eklenmez).

## 4. Akış

1. Kullanıcı soru veya yorum gönderir.
2. **BadWord kontrolü:** Metinde listeden bir kelime varsa → 400, “İçeriğinizde uygun olmayan ifadeler tespit edildi.”
3. **LLM çağrısı:** Cevap **RED** ise → `bad_words` SuggestedBadWord’e pending yazılır, kullanıcıya bildirim gider, 400 döner. **ONAY** veya hata/timeout ise → içerik kaydedilir.

## 5. Migration

```bash
cd marifetli/backend
python manage.py migrate moderation
```
