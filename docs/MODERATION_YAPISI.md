# Moderasyon Yapısı – Soru ve Yorum İnceleme

Bu dokümanda soru ve yorumları nasıl inceleyeceğinizi, **DB’ye ne zaman kaydettiğinizi** ve **görünürlüğü nasıl yönettiğinizi** (moderation_status, background task kuyruğu) netleştiriyoruz.

---

## Uygulanan akış: Celery + Redis

- Kullanıcı soru/cevap/blog yorumu gönderir → kayıt **hemen** DB’ye `moderation_status=0 (Pending)` ile yazılır.
- Aynı istek içinde **Celery task** kuyruğa eklenir (`moderate_content_task.delay(...)`). İstek hemen 201/200 döner.
- **Celery worker** Redis kuyruğundan task’ları alır; her task için:
  1. **BadWord** kontrolü (DB’deki kötü kelime listesi). Eşleşme varsa → `moderation_status=2` (Rejected), kullanıcıya bildirim, biter (LLM’e gidilmez).
  2. **LLM** çağrısı. RED → `moderation_status=2`, bildirim, `bad_words` SuggestedBadWord’e pending. ONAY → `moderation_status=1` (Approved), içerik sitede görünür.

Redis hem cache hem Celery broker olarak kullanılır (aynı REDIS_URL).

### Railway’de worker (Celery otomatik başlamaz)

**railway.json** hem web hem worker servisleri için aynı `start.sh`’i çalıştırabilir; hangi rolün çalışacağını **env değişkeni** belirler.

#### Servis yapısı

- **Backend (web) servisi:** Normal API / admin’i sunar.
- **Worker servisi:** Sadece Celery worker çalıştırır.

Her ikisi de aynı repo ve aynı `start.sh` dosyasını kullanır. `start.sh` içinde:

```bash
ROLE=${CELERY_WORKER:-0}  # 1 ise worker, aksi halde web
if [ "$ROLE" = "1" ]; then
  # Celery worker
  exec celery -A marifetli_project worker -l info
else
  # Web (gunicorn) + migrate
  python manage.py migrate --noinput
  exec gunicorn marifetli_project.wsgi:application --bind "0.0.0.0:$PORT" --workers 3 --timeout 120
fi
```

#### Adımlar

1. Railway Dashboard → Aynı projede **yeni servis** oluştur (Add Service) ve **aynı GitHub reposunu** seç (backend ile aynı).
2. Her iki serviste de **Start Command**: `sh start.sh` kalsın (override etmen gerekmiyor).
3. **Backend (web) servisi Variables:**
   - `CELERY_WORKER=0` **ya da hiç tanımlama** (varsayılan 0).
4. **Worker servisi Variables:**
   - `CELERY_WORKER=1` (bu servis Celery worker olarak çalışacak).
   - Backend ile aynı env’leri ver: `REDIS_URL`, `DATABASE_URL`, `SECRET_KEY`, `MODERATION_LLM_URL`, `MODERATION_LLM_PROMPT` vb.

Bu yapıda:
- Web servisi `start.sh` ile migrate + gunicorn çalıştırır.
- Worker servisi aynı `start.sh` ile Celery worker’ı çalıştırır (migrate yapmadan, sadece worker).

### Fallback: toplu komut

- Task’lar bir şekilde işlenmezse (worker kapalı vb.) bekleyen kayıtları toplu işlemek için:
  `python manage.py moderate_pending_content --limit 100`

### Loglama (DB’ye yazılmaz)

- **Celery worker** çalışırken: `cronjobs.tasks` → `Moderation task received: model=..., pk=...` (task alındı).
- **LLM çağrısı:** `moderation.services` → `Calling LLM moderation API: url=... payload_len=...` (istek atılmadan önce), sonra `LLM moderation result: status=... bad_words=...` (cevap alındıktan sonra).
- Bu loglar **Python logging** ile yazılır; konsola (veya `settings.LOGGING` ile yapılandırılmışsa dosyaya) gider. Veritabanına kayıt yapılmaz. Railway’de servis loglarında görürsün.

---

## Moderatör incelemesi

- **SuggestedBadWord:** LLM’den dönen kelimeler admin’de onaylanır/reddedilir.
- **Report:** Şikayet edilen içerikler sonradan inceleme için kullanılabilir.

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
