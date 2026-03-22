from django.core.management.base import BaseCommand
from decouple import config

from kids.models import KidsUser, KidsUserRole


class Command(BaseCommand):
    help = (
        "Kids için örnek öğretmen hesabı oluşturur veya günceller. "
        ".env: KIDS_DEMO_TEACHER_EMAIL, KIDS_DEMO_TEACHER_PASSWORD (yoksa güvenli olmayan varsayılanlar — sadece geliştirme)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Kayıt varsa şifreyi .env’deki (veya varsayılan) değere sıfırlar.",
        )

    def handle(self, *args, **options):
        email = config(
            "KIDS_DEMO_TEACHER_EMAIL",
            default="ogretmen-demo@marifetli.kids",
        ).strip().lower()
        password = config("KIDS_DEMO_TEACHER_PASSWORD", default="KidsDemo2025!")

        user = KidsUser.objects.filter(email__iexact=email).first()

        if user is None:
            user = KidsUser(
                email=email,
                first_name="Demo",
                last_name="Öğretmen",
                role=KidsUserRole.TEACHER,
            )
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Örnek öğretmen oluşturuldu: {email}"))
            self.stdout.write("  Varsayılan şifre: KidsDemo2025! (veya KIDS_DEMO_TEACHER_PASSWORD)")
        else:
            user.first_name = user.first_name or "Demo"
            user.last_name = user.last_name or "Öğretmen"
            user.role = KidsUserRole.TEACHER
            user.is_active = True
            if options["reset_password"]:
                user.set_password(password)
                self.stdout.write(self.style.SUCCESS(f"Şifre güncellendi: {email}"))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Kayıt zaten vardı; rol öğretmen yapıldı. Şifre değişmedi. "
                        "Sıfırlamak için: python manage.py create_kids_demo_teacher --reset-password"
                    )
                )
            user.save()

        self.stdout.write(f"  Kids giriş e-postası: {email}")
