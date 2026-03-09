# Moderasyon Yapısı – Soru ve Yorum İnceleme

Bu dokümanda soru ve yorumları nasıl inceleyeceğinizi, **DB’ye ne zaman kaydettiğinizi** ve **görünürlüğü nasıl yönettiğinizi** (is_visible benzeri alan, kuyruk vb.) netleştiriyoruz.

---

## Şu anki akış (önceden red)

- Kullanıcı soru/yorum gönderir.
- **BadWord** kontrolü → eşleşme varsa **kaydetmiyoruz**, 400 + mesaj.
- **LLM** çağrısı → **RED** ise yine **kaydetmiyoruz**, bildirim + 400; **ONAY** ise **hemen kaydedip yayınlıyoruz**.
- Yani: İnceleme “yayına almadan önce”; onaylanan içerik direkt görünür. Ayrı bir “beklemede” listesi yok.

Bu yapıda **moderatör incelemesi** şu an sadece:
- **SuggestedBadWord** (LLM’den dönen kelimeleri onaylamak/reddetmek),
- İsterseniz **Report** (şikayet) kayıtları üzerinden “sonradan” inceleme

ile yapılıyor.

---

## İki ana mimari seçenek

### 1) Önce kaydet, görünürlükle yönet (is_visible / moderation_status)

**Fikir:** Tüm soru ve yorumlar önce DB’ye yazılır; yayına alınma ayrı bir adımdır.

| Adım | Ne yapılır |
|------|------------|
| Gönderim | Kayıt oluşturulur, örn. `is_visible=False` veya `moderation_status='pending'`. |
| Liste/Detay API | Sadece `is_visible=True` (veya `approved`) kayıtlar döner. |
| Moderasyon | Admin’de “bekleyen” listesi; onaylayan kişi `is_visible=True` yapar (veya status’u `approved` yapar). |

**Artıları:** Hiçbir içerik kaybolmaz; önce kayıt var, sonra insan/otomasyon karar verir.  
**Eksileri:** Her listeleme/detayda filtre şart; yeni alan + migration; moderator arayüzü gerekir.

**Kuyruk:** Burada “kuyruk” = “moderation_status = pending” kayıtlar. Ekstra bir Redis/Celery kuyruğu zorunlu değil; admin’de “bekleyen sorular / bekleyen yorumlar” listesi yeterli. İsterseniz arka planda LLM’i çalıştırıp otomatik onay/red de yapabilirsiniz; yine de “insan incelemesi” için bu liste kuyruk görevi görür.

---

### 2) Önce inceleme (mevcut mantık), sonradan gizleme

**Fikir:** Yayına alma kararı **gönderim anında** verilir (BadWord + LLM). Sonradan şikayet veya inceleme ile içeriği **gizleyebilirsiniz**.

| Adım | Ne yapılır |
|------|------------|
| Gönderim | BadWord + LLM; ONAY → kaydet ve **hemen görünür**. RED → kaydetme. |
| Sonradan | Report geldiğinde veya moderator incelemesinde: ilgili soru/yorumu **gizle** (örn. `is_deleted=True` veya yeni alan `is_hidden_by_moderator=True`). |

**Artıları:** Basit; ek “bekleyen” listesi zorunlu değil; kullanıcı onaylanan içerikte hemen geri bildirim alır.  
**Eksileri:** RED verilen içerik DB’de yok (log isterseniz ayrı bir “reddedilen içerik logu” tutulabilir).

**Kuyruk:** “İncelenecek şeyler” = raporlanmış içerikler (AnswerReport; istersen QuestionReport) + isteğe bağlı “son N soru/yorum” listesi. Yani kuyruk = “moderatörün bakması gereken liste”, her yeni gönderi değil.

---

## Önerilen hibrit yapı

Hem mevcut akışı korumak hem de incelemeyi netleştirmek için:

1. **Yayına alma (önceden):**  
   Mevcut gibi kalsın: BadWord + LLM; RED → kaydetme, ONAY → kaydet ve **anında görünür**.

2. **Sonradan inceleme (reaktif):**  
   - Raporlanan içerikler (AnswerReport; gerekirse QuestionReport) admin’de listelensin.  
   - Moderator “gizle” / “sil” / “reddet” deyince ilgili soru/yorum **gizlensin** (zaten var olan `is_deleted` veya yeni bir `is_hidden_by_moderator` ile).

3. **İsteğe bağlı “her şey önce beklemede”:**  
   İleride “tüm yeni içerik önce onaylansın” derseniz:  
   - Question ve Answer’a `moderation_status` (örn. `pending` / `approved` / `rejected`) veya `is_visible` alanı ekleyin.  
   - Gönderimde kaydı `pending` (veya `is_visible=False`) ile oluşturun; listeleme/detayda sadece `approved` (veya `is_visible=True`) gösterin.  
   - Admin’de “bekleyen sorular” / “bekleyen yorumlar” sayfaları = kuyruk.  
   - Onaylayınca `approved` (veya `is_visible=True`) yapın.

Özet:

- **Şu an:** Kuyruk zorunlu değil; “inceleme” = BadWord + LLM (önceden) + Report’lar (sonradan).  
- **“Her şey önce incelemeden geçsin” dersen:** DB’ye önce kaydet + `is_visible` / `moderation_status` + admin’de bekleme listesi = yeterli kuyruk mekanizması; ayrıca Redis/Celery kuyruğu şart değil.

---

## Pratik adımlar (senaryoya göre)

- **Sadece raporlananları incelemek:**  
  Report modellerini kullanın; admin’de “çözülmemiş raporlar” listesi açın; moderator gizlesin/silsin.

- **Tüm yeni içeriği onay sırasına almak:**  
  1. Question / Answer’a `moderation_status` veya `is_visible` ekleyin (migration).  
  2. Create API’de kaydı `pending` (veya `is_visible=False`) ile oluşturun.  
  3. List/Detail API’lerde sadece `approved` (veya `is_visible=True`) döndürün.  
  4. Admin’de “pending” kayıtları listele; “Onayla” / “Reddet” aksiyonları ile güncelleyin.

Bu yapı ile moderasyonu “önce DB’ye kaydet, is_visible/moderation_status ile yönet; kuyruk = beklemedeki kayıtlar” şeklinde kurgulayabilirsiniz. İsterseniz bir sonraki adımda hangi senaryoyu (sadece report / her şey pending) seçtiğinizi söyleyin; buna göre alan adları ve API filtrelerini netleştirebiliriz.
