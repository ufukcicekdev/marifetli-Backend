"""
Gemini API'yi test eder: örnek soru ve cevap üretir, çıktıyı yazdırır.
Kullanım:
  python manage.py test_gemini
  python manage.py test_gemini --category "Dikiş Nakış"
  python manage.py test_gemini --questions 3
"""
from django.core.management.base import BaseCommand
from django.conf import settings

from bot_activity.gemini_client import (
    generate_question_for_category,
    generate_answer_for_question,
)


class Command(BaseCommand):
    help = "Gemini API ile örnek soru/cevap üretir, çıktıyı gösterir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            type=str,
            default=None,
            help="Test edilecek kategori adı (yoksa birkaç örnek kategori denenir).",
        )
        parser.add_argument(
            "--questions",
            type=int,
            default=2,
            help="Kaç örnek soru üretilecek (varsayılan 2).",
        )
        parser.add_argument(
            "--answer",
            action="store_true",
            help="Üretilen bir soruya örnek cevap da üret.",
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
        if not api_key:
            self.stderr.write(
                self.style.ERROR("GEMINI_API_KEY tanımlı değil. .env içinde ayarlayın.")
            )
            return

        model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        self.stdout.write(
            self.style.SUCCESS(f"Model: {model} | API key: ...{api_key[-4:] if len(api_key) > 4 else '****'}\n")
        )

        categories = (
            [options["category"]]
            if options["category"]
            else ["Yemek Tarifleri", "El İşleri", "Dikiş Nakış"]
        )
        n = min(options["questions"], len(categories) * 2)
        genders = ["kadın", "erkek"]

        for i in range(n):
            cat = categories[i % len(categories)]
            gender = genders[i % 2]
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.WARNING(f"[{i+1}] Kategori: {cat} | Cinsiyet: {gender}"))
            self.stdout.write("=" * 60)

            result = generate_question_for_category(cat, gender)
            title = result.get("title", "") or ""
            desc = result.get("description", "") or ""
            self.stdout.write("  Başlık: " + title)
            self.stdout.write("  Açıklama: " + desc)
            if result.get("content"):
                self.stdout.write("  İçerik: " + (result.get("content", "") or "")[:500])

            if options["answer"] and i == 0:
                self.stdout.write("\n  --- Örnek cevap ---")
                answer_text = generate_answer_for_question(
                    result.get("title", ""),
                    result.get("description", ""),
                    [],
                    gender,
                )
                self.stdout.write(f"  Cevap: {answer_text}")

        self.stdout.write("\n" + self.style.SUCCESS("Test tamamlandı."))
