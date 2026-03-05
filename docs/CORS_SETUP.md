# CORS Ayarı

Frontend (www.marifetli.com.tr) ile backend farklı domain’de olduğu için tarayıcı CORS kurallarını uygular. Backend’in hangi origin’lere izin verdiği **.env** içindeki `FRONTEND_URL` ile belirlenir.

## Ne yapılır?

1. **Backend .env** dosyasında site adresini tanımlayın:
   ```env
   # Yerel geliştirme
   FRONTEND_URL=http://localhost:3000

   # Canlı (production)
   FRONTEND_URL=https://www.marifetli.com.tr
   ```

2. **Canlı (Railway vb.)** ortamda backend’in **environment variables** kısmına mutlaka ekleyin:
   ```env
   FRONTEND_URL=https://www.marifetli.com.tr
   ```
   Bu değer yoksa CORS listesinde sadece localhost kalır ve production frontend’den gelen istekler CORS hatası alır.

## Otomatik eklenen origin’ler

- `FRONTEND_URL` değeri CORS listesine eklenir.
- `https://www.marifetli.com.tr` ise `https://marifetli.com.tr` de eklenir (ve tersi).
- Her zaman: `http://localhost:3000`, `http://127.0.0.1:3000`.

## İsteğe bağlı: Tam liste

Tüm listeyi kendiniz vermek isterseniz:

```env
CORS_ALLOWED_ORIGINS=https://www.marifetli.com.tr,https://marifetli.com.tr,http://localhost:3000
```

Bu tanımlıysa `FRONTEND_URL` CORS için kullanılmaz; sadece e-posta ve OAuth redirect için kullanılır.
