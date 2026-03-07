# Google ile giriş kurulumu

## 1. Google Cloud Console

1. [Google Cloud Console](https://console.cloud.google.com/) → Proje seç veya yeni proje oluştur.
2. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**.
3. Consent screen ayarlanmamışsa önce **OAuth consent screen** (Test veya Production) yapılandır.
4. Application type: **Web application**.
5. **Authorized redirect URIs** kısmına backend callback adresini ekle:
   - `http://localhost:8000/api/auth/complete/google-oauth2/`
   - `http://127.0.0.1:8000/api/auth/complete/google-oauth2/` (yerel için ikisini de ekle)
   - Canlı: `https://web-production-5404d.up.railway.app/api/auth/complete/google-oauth2/`
6. **Create** → Client ID ve Client Secret’ı kopyala.

## 2. Backend .env

```env
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=your_client_id_here
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your_client_secret_here
FRONTEND_URL=http://localhost:3000
# OAuth sonrası yönlendirme backend’e aynı host’tan gitsin diye (session cookie için). Boşsa yerel için http://localhost:8000 kullanılır.
# BACKEND_URL=http://localhost:8000
# Production:
# FRONTEND_URL=https://www.marifetli.com.tr
# BACKEND_URL=https://api.marifetli.com.tr
```

Production’da `FRONTEND_URL` canlı frontend adresi olmalı (production: `https://www.marifetli.com.tr`). Session cookie’nin kaybolmaması için canlıda `BACKEND_URL` de backend’in tam adresi olmalı.

## 3. Akış

1. Kullanıcı “Google ile devam et”e tıklar → frontend **önce** `/api/auth/start-google-login/` ile backend session’ı temizler, sonra `/api/auth/login/google-oauth2/` ile Google’a gider.
2. Backend Google’a yönlendirir.
3. Kullanıcı Google’da giriş yapar, izin verir.
4. Google kullanıcıyı backend’e geri gönderir: `/api/auth/complete/google-oauth2/`.
5. Backend pipeline’da kullanıcıyı oluşturur/eşleştirir, **pipeline son adımında** JWT üretir ve doğrudan frontend’e yönlendirir: `FRONTEND_URL/auth/callback#access=...&refresh=...` (session kullanılmaz).
6. Frontend `/auth/callback` sayfası hash’ten token’ları alır, kaydeder ve ana sayfaya yönlendirir.

## 4. Sorun giderme

- **Redirect URI mismatch**: Google Console’daki redirect URI, backend’in tam adresiyle birebir aynı olmalı (sonunda `/` dahil).
- **403 / Access blocked**: OAuth consent screen’de test kullanıcısı ekle (Production’a almadıysan).
- **Key/Secret boş**: `.env` dosyasında `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` ve `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET` dolu olmalı.
- **401 / Invalid key/secret, perhaps expired** (token değişiminde hata):
  1. [Google Cloud Console](https://console.cloud.google.com/) → Credentials → ilgili OAuth 2.0 Client ID’ye tıkla.
  2. **Client ID** ve **Client secret** değerlerini `.env` ile birebir karşılaştır (boşluk, fazladan karakter olmasın).
  3. Client secret’ı **yeniden oluşturduysan** eski secret geçersizdir; yeni secret’ı `.env`’e yapıştır.
  4. Yerel test için **Authorized redirect URIs** listesinde şunlardan biri tam olarak olmalı:
     - `http://127.0.0.1:8000/api/auth/complete/google-oauth2/`
     - veya `http://localhost:8000/api/auth/complete/google-oauth2/`
  5. Değişiklikten sonra backend’i yeniden başlat.
- **“Oturum alınamadı” / not_authenticated**: Google’dan dönüşte session cookie backend’e gitmiyordur. Backend terminalinde uyarı log’unda `session_keys`, `_auth_user_id` ve `cookies` değerlerine bak. Boş session/cookie ise: (1) Girişi frontend’den **aynı sekmede** yap (linke tıklayıp backend → Google → backend akışı aynı sekmede olsun). (2) Canlıda `BACKEND_URL` .env’de backend’in tam adresi olarak tanımlı olsun. (3) Tarayıcıda backend ile frontend aynı domain’de değilse (localhost:3000 vs localhost:8000) cookie’ler port bazlı ayrıldığı için sorun olmaz; akışın tamamı backend host’unda (login → complete → oauth-success) olmalı.
