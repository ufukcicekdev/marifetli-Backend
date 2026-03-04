# Google ile giriş kurulumu

## 1. Google Cloud Console

1. [Google Cloud Console](https://console.cloud.google.com/) → Proje seç veya yeni proje oluştur.
2. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**.
3. Consent screen ayarlanmamışsa önce **OAuth consent screen** (Test veya Production) yapılandır.
4. Application type: **Web application**.
5. **Authorized redirect URIs** kısmına backend callback adresini ekle:
   - Yerel: `http://localhost:8000/api/auth/complete/google-oauth2/`
   - Canlı: `https://your-backend-domain.com/api/auth/complete/google-oauth2/`
6. **Create** → Client ID ve Client Secret’ı kopyala.

## 2. Backend .env

```env
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=your_client_id_here
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your_client_secret_here
FRONTEND_URL=http://localhost:3000
```

Production’da `FRONTEND_URL` canlı frontend adresi olmalı (örn. `https://marifetli.com`).

## 3. Akış

1. Kullanıcı “Google ile devam et”e tıklar → frontend backend’e yönlendirir: `/api/auth/login/google-oauth2/`.
2. Backend Google’a yönlendirir.
3. Kullanıcı Google’da giriş yapar, izin verir.
4. Google kullanıcıyı backend’e geri gönderir: `/api/auth/complete/google-oauth2/`.
5. Backend kullanıcıyı oluşturur veya eşleştirir, JWT üretir ve frontend’e yönlendirir: `FRONTEND_URL/auth/callback?access=...&refresh=...`.
6. Frontend `/auth/callback` sayfası token’ları alır, kaydeder ve ana sayfaya yönlendirir.

## 4. Sorun giderme

- **Redirect URI mismatch**: Google Console’daki redirect URI, backend’in tam adresiyle birebir aynı olmalı (sonunda `/` dahil).
- **403 / Access blocked**: OAuth consent screen’de test kullanıcısı ekle (Production’a almadıysan).
- **Key/Secret boş**: `.env` dosyasında `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` ve `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET` dolu olmalı.
