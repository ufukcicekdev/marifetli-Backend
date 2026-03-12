# Firebase (FCM) Push Bildirimleri – Ne Yapman Lazım?

Backend’de push bildirimleri **Firebase Cloud Messaging (FCM)** ile gönderiliyor. Aşağıdaki adımları tamamladığında tarayıcıda/mobilde push bildirim çalışır.

---

## Firebase sayfasında tam olarak nasıl ilerleyeceksin

Console’u açtıysan ekranda büyük ihtimalle şunlardan biri var. Hangisi varsa ona göre ilerle.

---

### Senaryo A: “Proje ekle” / proje listesi görüyorsan

1. **“Proje ekle”** (veya “Add project”) butonuna tıkla.
2. **Proje adı** yaz (örn. `Marifetli`) → **Devam**.
3. Google Analytics’i **şimdilik açma** (isteğe bağlı) → **Proje oluştur**.
4. Bittiğinde **“Projeye geç”** / **“Continue to console”** de.
5. Sonra aşağıdaki **“Servis hesabı JSON’u al (backend için)”** bölümüne geç.

---

### Senaryo B: Zaten bir proje seçili, sol menü görüyorsan

Sol tarafta **Build**, **Engage**, **Release** gibi menüler var. Şimdilik bunlara girmene gerek yok.

1. Sol altta **proje adının yanındaki dişli (⚙️) ikona** tıkla.
2. Açılan menüden **“Proje ayarları”** / **“Project settings”** seç.
3. Açılan sayfada üstte **“Genel”** / **“General”** sekmesi olacak; öyle kalsın.
4. Sayfayı **aşağı kaydır**.
5. **“Servis hesapları”** / **“Service accounts”** başlığını bul.
6. O bölümde **“Yeni özel anahtar oluştur”** / **“Generate new private key”** butonuna tıkla.
7. Uyarıda **“Anahtar oluştur”** / **“Generate key”** de → bir **JSON dosyası** inecek.
8. Bu dosyayı güvenli bir yere kaydet (örn. bilgisayarında `İndirilenler`). Sonra bu dosyayı backend klasörüne taşıyacaksın (aşağıda anlatılıyor).

---

### Servis hesabı JSON’u al (backend için) – tekrar özet

| Sıra | Ekranda ne yapacaksın |
|------|------------------------|
| 1 | Sol altta **dişli ikon (⚙️)** → **Proje ayarları** |
| 2 | Üstte **Genel** sekmesi seçili olsun |
| 3 | Sayfayı **aşağı kaydır** |
| 4 | **“Servis hesapları”** bölümünü bul |
| 5 | **“Yeni özel anahtar oluştur”** butonuna tıkla |
| 6 | Açılan pencerede **“Anahtar oluştur”** de → JSON dosyası inecek |
| 7 | İnen dosyayı (örn. `marifetli-xxxxx-firebase-adminsdk-xxxxx.json`) backend’e koy: `backend/config/firebase-service-account.json` (önce `backend/config` klasörünü oluştur) |
| 8 | Backend’deki `.env` dosyasına şunu ekle: `FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json` |

Bunları yaptıysan **backend tarafı** tamam. Push’ların gitmesi için backend’in bu JSON’a ihtiyacı var.

---

### Bu JSON dosyası Git’e gitmeyecek – production’da nasıl olacak?

**Önemli:** `firebase-service-account.json` içinde **gizli anahtar** var. Bu dosyayı **asla Git’e ekleme**. `.gitignore`’da zaten var; yanlışlıkla `git add` etme.

- **Bilgisayarında (yerel):** Dosyayı `backend/config/` içine koyup `.env`’de `FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json` kullan. Bu dosya Git’e commit edilmez, sadece senin makinede kalır.

- **Sunucuda (Railway, Render vb.):** İki yol var:

  **Yol 1 – Ortam değişkeni (en kolay):**  
  JSON dosyasının **içeriğini tek satır** yapıp sunucunun ortam değişkenine yapıştır. Backend hem dosya yolu hem de “JSON’u direkt env’den oku” destekliyor.

  1. `firebase-service-account.json` dosyasını aç, tüm içeriği kopyala.
  2. Tek satır yap: satır sonlarını sil veya bir metin editöründe “tek satıra indir”.
  3. Railway / Render / vb. → Proje → **Variables** (veya **Environment**) → **Yeni değişken**:
     - İsim: `FIREBASE_CREDENTIALS_JSON`
     - Değer: Yapıştırdığın tek satır JSON (tırnak içine almana gerek yok; platform tek satır olarak saklar).
  4. Sunucuda **dosya yolu kullanma**: `FIREBASE_CREDENTIALS_PATH`’i **tanımlama** veya boş bırak. `FIREBASE_CREDENTIALS_JSON` dolu olduğu sürece backend onu kullanır.

  **Yol 2 – Dosyayı sunucuya koymak:**  
  Hosting’in “secret file” / “volume” özelliği varsa JSON dosyasını oraya yükleyip `FIREBASE_CREDENTIALS_PATH` ile tam yolu verirsin (örn. `/app/config/firebase-service-account.json`). Dosya Git’ten gelmez, deploy sırasında sen eklenmiş olursun.

---

### (İsteğe bağlı) Tarayıcıda push almak – Web uygulaması + VAPID

Sadece backend’e push göndertmek yeterliyse bunu atlayabilirsin. Tarayıcıda da bildirim pop-up’ı istiyorsan:

1. Yine **Proje ayarları** (dişli → Proje ayarları) → **Genel** sekmesi.
2. Sayfayı aşağı kaydır; **“Uygulamanız”** / **“Your apps”** bölümüne gel.
3. **“</>” (Web)** ikonuna tıkla → uygulama adı yaz (örn. **Marifetli Web**) → **Kaydet**.
4. Açılan kutuda **apiKey, projectId, appId, messagingSenderId** vb. görünecek; bunları bir yere kopyala (frontend `.env.local` için lazım).
5. Sonra sol menüden **“Build”** → **“Cloud Messaging”** aç.
6. **“Web Push sertifikaları”** bölümünde **“Anahtar çifti oluştur”** varsa tıkla → çıkan **VAPID anahtarını** da kopyala; frontend’de `NEXT_PUBLIC_FIREBASE_VAPID_KEY` olarak kullanacaksın.

---

## Adım 1: Firebase projesi

1. [Firebase Console](https://console.firebase.google.com/) → **Proje ekle** veya mevcut projeyi seç.
2. Proje oluşturduysan **Google Analytics** isteğe bağlı (şimdilik atlayabilirsin).

---

## Adım 2: Backend – servis hesabı (push göndermek için)

Backend’in FCM’e “bu uygulama adına push gönder” diyebilmesi için **servis hesabı JSON** lazım.

1. Firebase Console → **Proje ayarları** (dişli) → **Genel** sekmesi.
2. Aşağı kaydır → **Servis hesapları**.
3. **“Yeni özel anahtar oluştur”** → JSON indir.
4. İndirdiğin dosyayı backend’de güvenli bir yere koy, örneğin:
   - `backend/config/firebase-service-account.json`
   - veya `backend/firebase-service-account.json`
5. Bu dosyayı **asla Git’e ekleme** (`.gitignore`’da zaten var).

---

## Adım 3: Backend – .env

Backend’in çalıştığı dizindeki `.env` dosyasına ekle:

```env
# Push bildirimleri (FCM) – servis hesabı dosya yolu
FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json
```

- Path, `manage.py` çalıştığın dizine göre (örn. `backend/`). Tam path de yazabilirsin:  
  `FIREBASE_CREDENTIALS_PATH=/var/app/config/firebase-service-account.json`

---

## Adım 4: Backend – bağımlılık

```bash
cd backend
pip install firebase-admin
```

(Zaten `requirements.txt`’te var; `pip install -r requirements.txt` yaptıysan kuruludur.)

---

## Adım 5: Frontend – tarayıcıda push almak (opsiyonel)

Kullanıcı tarayıcıda “Bildirimlere izin ver” deyip token alacak; backend bu token’ı kaydedip o cihaza push atacak.

### 5.1 Web uygulaması ekle

1. Firebase Console → **Proje ayarları** → **Genel**.
2. **“Uygulamanızı ekleyin”** → **Web** (</> ikonu).
3. Uygulama adı ver (örn. “Marifetli Web”) → **Kaydet**.
4. Açılan **Firebase config** objesini kopyala (apiKey, authDomain, projectId, vb.).

### 5.2 VAPID anahtarı (Web Push için)

1. Firebase Console → **Proje ayarları** → **Cloud Messaging** sekmesi.
2. **“Web Push sertifikaları”** bölümünde **“Anahtar çifti oluştur”** (yoksa).  
   Bu **VAPID key**; frontend’de FCM token alırken kullanılacak.

### 5.3 Frontend .env

Frontend projesinde (Next.js) `.env.local` oluştur veya aç, Firebase config’ten gelen değerleri yaz:

```env
# Firebase Web (push bildirimleri – opsiyonel)
NEXT_PUBLIC_FIREBASE_API_KEY=AIza...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=marifetli-...
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456:web:abc...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_VAPID_KEY=BAbc...xyz
```

- `NEXT_PUBLIC_FIREBASE_VAPID_KEY` = Cloud Messaging’te oluşturduğun **Web Push VAPID key**.

### 5.4 Frontend’de token alıp backend’e göndermek

Giriş yapan kullanıcı için:

1. Tarayıcıda bildirim izni iste: `Notification.requestPermission()`.
2. Firebase JS SDK ile FCM token al: `getToken(messaging, { vapidKey: NEXT_PUBLIC_FIREBASE_VAPID_KEY })`.
3. Bu token’ı backend’e kaydet:  
   `POST /api/notifications/fcm-register/` body: `{ "token": "...", "device_name": "Chrome" }`  
   (Frontend’de `api.registerFCMToken(fcmToken, 'Chrome')` zaten var; sadece FCM SDK’yı kurup token’ı alıp bu metodu çağırman yeterli.)

Firebase JS paketi: `npm install firebase` (v10+).  
Örnek kullanım: [Firebase Web: FCM token almak](https://firebase.google.com/docs/cloud-messaging/js/client).

---

## Özet tablo

| Ne | Nerede | Zorunlu? |
|----|--------|----------|
| Firebase projesi | Firebase Console | Evet |
| Servis hesabı JSON | Backend’e koy, .env’de path ver | Push göndermek için evet |
| `FIREBASE_CREDENTIALS_PATH` | Backend `.env` | Push göndermek için evet |
| `firebase-admin` | Backend `pip install` | Evet |
| Web uygulaması + config + VAPID | Firebase Console + frontend `.env.local` | Sadece tarayıcıda push almak istiyorsan |
| Frontend’de FCM SDK + izin + `registerFCMToken` | Next.js uygulaması | Tarayıcı push için evet |

---

## Test (PC’de sayfayı açtım, nasıl test edeceğim?)

1. **Backend’in çalıştığından emin ol:** `python manage.py runserver` (veya canlıda backend ayakta olsun).
2. **Frontend’de giriş yap** (tarayıcıda siteyi aç, giriş yap).
3. **Bildirimler sayfasına git:** `/bildirimler`.
4. **Tarayıcı push için:** Frontend `.env.local` içinde `NEXT_PUBLIC_FIREBASE_VAPID_KEY`, `NEXT_PUBLIC_FIREBASE_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_APP_ID`, `NEXT_PUBLIC_FIREBASE_API_KEY`, `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` olsun (Firebase Console → Proje ayarları → Genel → Web uygulamanız → config). Sayfayı açınca "Bildirimlere izin ver" çıkar; izin verirsen token otomatik kaydedilir.
5. **"Test push gönder" butonuna tıkla** (Bildirimler sayfasında). Cihaz kayıtlıysa birkaç saniye içinde "Marifetli test – Push bildirimleri çalışıyor." bildirimi gelir. "Kayıtlı cihaz yok" derse önce bildirim iznini verip sayfayı yenile veya `.env.local` Firebase config’ini tamamla.
6. **Terminal’den test:** `python manage.py send_test_push KULLANICI_ADI` — o kullanıcıya kayıtlı cihaz varsa push gider.

---

## Test (özet)

- **Backend:** `.env`’de `FIREBASE_CREDENTIALS_PATH` doğru ve dosya var. Bir kullanıcıya ait FCM token’ı (örn. Django admin’den veya fcm-register ile) veritabanında kayıtlı olmalı. O kullanıcı için tetiklenen bir bildirim (cevap, beğeni vb.) push olarak gider.
- **Frontend:** Giriş yaptıktan sonra bildirim izni verilir, token alınır ve `registerFCMToken` ile backend’e gönderilir. Sonra o kullanıcıya giden bildirimler tarayıcıda push olarak görünür.

Config eklemezsen bildirimler yine oluşur (veritabanı + uygulama içi liste); sadece **push** (tarayıcı/mobil bildirim) gönderilmez.

---

## Sorun giderme: "401 Unauthorized" / "token-subscribe-failed"

Tarayıcıda "Bildirimleri aç"a bastığında şu hata çıkarsa:

- **"Request is missing required authentication credential"**
- **"POST https://fcmregistrations.googleapis.com/... 401 (Unauthorized)"**
- **"messaging/token-subscribe-failed"**

Bunun nedeni **Google Cloud'da Web API anahtarının kısıtlı olması** veya **FCM API'nin kapalı olması**dır. Şunları yap:

### 1. Firebase Cloud Messaging API açık mı?

1. [Google Cloud Console](https://console.cloud.google.com/) → projeyi seç (Firebase projenle aynı).
2. **API'ler ve Hizmetler** → **Kitaplık**.
3. **"Firebase Cloud Messaging API"** ara → **Etkinleştir** (Enable). Kapalıysa aç.

### 2. Web API anahtarı kısıtlamaları

Frontend'de kullandığın **API anahtarı** (Firebase config'teki `apiKey`) Google Cloud'da kısıtlı olabilir.

1. [Google Cloud Console](https://console.cloud.google.com/) → projeyi seç.
2. **API'ler ve Hizmetler** → **Kimlik bilgileri**.
3. **API anahtarları** bölümünde kullandığın anahtarı bul (Firebase'te "Web API Key" olarak geçer).
4. Anahtara tıkla (düzenle).

**Uygulama kısıtlamaları:**

- **Yok** ise: Anahtar tüm referrer'larda çalışır; localhost dahil. 401 başka bir nedendir (FCM API kapalı vb.).
- **HTTP referanslar** seçiliyse: Mutlaka şunları ekle:
  - `http://localhost:*`
  - `http://127.0.0.1:*`
  - Canlı site: `https://www.marifetli.com.tr/*` (kendi domain'in neyse onu ekle).

**API kısıtlamaları:**

- **Tüm API'lere izin ver** seçiliyse sorun olmaz.
- **Sadece belirli API'lere kısıtla** seçiliyse listeye **"Firebase Cloud Messaging API"** (ve varsa **"FCM Registrations API"**) ekle.

Kaydedip birkaç dakika bekle; tarayıcıda sayfayı yenileyip tekrar "Bildirimleri aç"ı dene.

### 3. Hâlâ 401 alıyorsan: Anahtarı geçici olarak kısıtlamasız dene

Bunun API anahtarından kaynaklandığını netleştirmek için:

1. [Google Cloud Console](https://console.cloud.google.com/) → **API'ler ve Hizmetler** → **Kimlik bilgileri**.
2. **+ Kimlik bilgisi oluştur** → **API anahtarı**.
3. Yeni anahtar oluşur. **Kısıtlamaları düzenle** açılmasın; **İptal** de (şimdilik kısıtlama yok).
4. Bu yeni anahtarın değerini kopyala.
5. Frontend `.env.local` içinde `NEXT_PUBLIC_FIREBASE_API_KEY=` değerini bu yeni anahtar ile değiştir.
6. Sayfayı tam yenile (Ctrl+Shift+R) ve tekrar "Bildirimleri aç"ı dene.

Eğer bu kısıtlamasız anahtar ile çalışıyorsa sorun kesinlikle eski anahtarın **uygulama** veya **API** kısıtlamalarındandır. Sonra ya bu yeni anahtarda sadece ihtiyacın olan kısıtlamaları ekle (HTTP referanslar + FCM API) ya da eski anahtarı düzelterek kullan.

**Dikkat:** Anahtarın, Firebase projenin (marifetli-3d2d9) **aynı Google Cloud projesine** ait olduğundan emin ol. Firebase Console → Proje ayarları → Genel → "Proje Kimliği" ile Google Cloud’daki proje aynı olmalı.
