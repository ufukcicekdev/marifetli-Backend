# Firebase (FCM) Push Bildirimleri Kurulumu

Backend’de push bildirimleri için Firebase Cloud Messaging kullanılıyor. Config’i sen ekleyeceksin.

## 1. Firebase Console

1. [Firebase Console](https://console.firebase.google.com/) → Proje seç / oluştur
2. Proje Ayarları → Genel → “Servis hesapları” → “Yeni özel anahtar oluştur” → JSON indir
3. Bu dosyayı backend’de güvenli bir yere koy (örn. `backend/config/firebase-service-account.json`) ve **versiyon kontrolüne ekleme** (`.gitignore`’a ekle)

## 2. Backend (.env)

```env
# Push bildirimleri için (opsiyonel)
FIREBASE_CREDENTIALS_PATH=config/firebase-service-account.json
```

Path, `manage.py` çalıştığı dizine göre veya tam path olabilir.

## 3. Bağımlılık

```bash
pip install firebase-admin
```

(Zaten `requirements.txt` içinde.)

## 4. Frontend (tarayıcı push – opsiyonel)

Tarayıcıda push almak için:

1. Firebase Console → Proje ayarları → Genel → “Web uygulamanızı ekleyin” → config objesini al
2. Frontend `.env.local` içine ekle:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
...
```

3. Giriş yapan kullanıcı için FCM token alıp backend’e gönder:

```ts
// Örnek: /notifications/fcm-register/ endpoint’ine POST { token, device_name }
await api.registerFCMToken(fcmToken, 'Chrome');
```

Firebase JS SDK ile token almak için `getToken(messaging, { vapidKey: '...' })` kullanılır (VAPID key Firebase Console’dan alınır).

Config eklenmezse bildirimler yine oluşur; sadece push gönderilmez, e-posta (ayarlar açıksa) ve uygulama içi bildirimler çalışır.
