# Site Ayarları (Admin Panel)

İletişim sayfası, sosyal medya linkleri ve Google Analytics / Search Console ayarları Django Admin üzerinden yönetilir.

## Nerede?

- **Django Admin** → **Site ayarları** (Core uygulaması)
- **Sosyal medya linkleri** → Ayrı menü: "Sosyal medya linkleri"

## Site ayarları (tek kayıt)

- **İletişim:** E-posta, telefon, adres, kısa açıklama (iletişim sayfasında gösterilir)
- **Google Analytics ID:** GA4 Ölçüm ID (örn. `G-XXXXXXXXXX`) — doldurulursa sitede GA4 script yüklenir
- **Google Search Console meta:** Doğrulama meta etiketinin `content` değeri — doldurulursa `<meta name="google-site-verification" content="..." />` head’e eklenir

## Sosyal medya linkleri

- Platform: Facebook, Twitter/X, Instagram, YouTube, LinkedIn, TikTok veya Diğer
- URL: Hesap sayfası linki
- Label: İsteğe bağlı görünen ad
- Sıra: Listeleme sırası (küçük numara önce)
- Aktif: İşaretli olanlar iletişim sayfasında ve gerekirse footer’da gösterilir

## İlk kurulum

1. Admin’de **Site ayarları**ndan bir kayıt oluşturun (iletişim bilgileri ve isteğe bağlı GA/GSC).
2. **Sosyal medya linkleri**nden her platform için bir kayıt ekleyin.
3. Frontend iletişim sayfası (`/iletisim`) ve layout otomatik olarak bu verileri kullanır.
