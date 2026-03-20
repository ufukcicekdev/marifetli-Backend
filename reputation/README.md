# İtibar ve rozetler

## Mevcut kullanıcılar için rozet senkronizasyonu

Davranış rozetleri (Hoş Geldin, Yardımsever, Usta Paylaşımcı, Popüler) ve itibar eşiği (milestone) rozetleri ile `User.current_level_title` alanını toplu güncellemek için:

```bash
cd backend
python manage.py backfill_reputation_badges
```

- Tek kullanıcı: `--user-id 123`
- Deneme: `--dry-run`

Bu komut idempotent çalışır: zaten var olan `UserBadge` kayıtlarını tekrar oluşturmaz.

## API

- `GET /api/gamification/public/` — **Giriş gerekmez.** Seviye tablosu, rozet listesi ve ödül mantığı özeti (tanıtım modalı).
- `GET /api/auth/me/gamification/` — Giriş yapmış kullanıcı için kişisel yol haritası (UI teşvik metinleri). Puan veya rozet değiştirmez.
