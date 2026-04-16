# MEB Öğretim Programları — Komutlar

## Kurulum

```bash
cd marifetli/backend
source venv/bin/activate
pip install requests beautifulsoup4
```

---

## 1. Scraper — MEB'den veri çek

Tüm ders → sınıf → ünite sayfalarını tymm.meb.gov.tr'den çekip DB'ye kaydeder.

```bash
# 2025/2026 eğitim yılı için çek ve kaydet
python manage.py sync_meb_programlari --yil 2025/2026

# Sadece listele, DB'ye yazma
python manage.py sync_meb_programlari --yil 2025/2026 --dry-run

# İstekler arası beklemeyi ayarla (varsayılan: 0.8s)
python manage.py sync_meb_programlari --yil 2025/2026 --delay 1.5
```

---

## 2. AnythingLLM'e gönder

DB'deki kayıtları AnythingLLM workspace'ine klasör yapısıyla yükler.

**Sunucu:** `https://anythingllm-production-6381.up.railway.app`  
**Workspace:** `ogretmen-ai`

```bash
# .env'deki bilgilerle gönder (önerilen)
python manage.py push_to_anythingllm --yil 2025/2026

# Bilgileri elle girerek gönder
python manage.py push_to_anythingllm \
  --url https://anythingllm-production-6381.up.railway.app \
  --api-key PPC26XE-7ZH4H9T-GQQQQKY-KC173MZ \
  --workspace ogretmen-ai \
  --yil 2025/2026

# Sadece liste — yükleme yapma
python manage.py push_to_anythingllm --yil 2025/2026 --dry-run

# İstekler arası beklemeyi ayarla (varsayılan: 1.0s)
python manage.py push_to_anythingllm --yil 2025/2026 --delay 1.5
```

> **Not:** Her kayıt için 2 adım atılır:
> 1. `upload-link` — sayfayı indirip sisteme işler
> 2. `update-embeddings` — workspace'e (ogretmen-ai) ekler

### .env değişkenleri

`.env` dosyasında tanımlı — komut satırında verme gerek yok:

```env
ANYTHINGLLM_URL=https://anythingllm-production-6381.up.railway.app
ANYTHINGLLM_API_KEY=PPC26XE-7ZH4H9T-GQQQQKY-KC173MZ
ANYTHINGLLM_WORKSPACE=ogretmen-ai
```

---

## Tam akış

```bash
# 1. MEB'den linkleri çek → DB'ye kaydet
python manage.py sync_meb_programlari --yil 2025/2026

# 2. Her linkin içeriğini çekip .md olarak kaydet
python manage.py scrape_to_files --yil 2025/2026

# 3. .md dosyalarını AnythingLLM'e yükle → embed et → local dosyayı sil
python manage.py push_to_anythingllm --yil 2025/2026
```

---

## Klasör yapısı (AnythingLLM)

```
2025-2026/
├── ilkokul/
│   ├── 1.sinif/
│   │   └── ilkokul-matematik-dersi/
│   │       └── uniteler/    ← her ünite ayrı URL
│   └── 5.sinif/
│       └── fen-bilimleri-dersi/
│           └── uniteler/
├── ortaokul/
│   └── 8.sinif/
│       └── ...
├── ortaogretim/
│   └── 11.sinif/
│       └── tarih-dersi/
│           └── uniteler/
└── anaokulu/
    └── 36-48-ay/
        └── okul-oncesi/
```
