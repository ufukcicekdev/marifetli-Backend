"""
Bot kullanıcı oluşturma ve aktivite döngüsü.
Kullanım:
  python manage.py run_bot_activity              # Eksik botları oluşturur, bir tur aktivite çalıştırır
  python manage.py run_bot_activity --create-only   # Sadece 100 bot oluşturur
  python manage.py run_bot_activity --activity-only # Sadece aktivite (soru/cevap) çalıştırır
  python manage.py run_bot_activity --questions 10  # Tur başına 10 soru
"""
import logging

from django.core.management.base import BaseCommand

from bot_activity.services import create_bot_users, run_activity_cycle, is_bot_enabled

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Bot kullanıcıları oluşturur ve/veya soru/cevap aktivitesi çalıştırır."

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-only",
            action="store_true",
            help="Sadece 100 bot kullanıcı oluştur, aktivite çalıştırma.",
        )
        parser.add_argument(
            "--activity-only",
            action="store_true",
            help="Sadece aktivite döngüsü çalıştır (bot oluşturma).",
        )
        parser.add_argument(
            "--questions",
            type=int,
            default=5,
            help="Bir turda oluşturulacak soru sayısı (varsayılan 5).",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Oluşturulacak toplam bot sayısı (varsayılan 100).",
        )

    def handle(self, *args, **options):
        if not is_bot_enabled():
            self.stderr.write(
                self.style.WARNING(
                    "BOT_USERS_ENABLED=True ve GEMINI_API_KEY .env'de tanımlı olmalı."
                )
            )
            return

        create_only = options["create_only"]
        activity_only = options["activity_only"]
        questions = max(1, min(options["questions"], 20))
        count = max(1, min(options["count"], 200))

        if not activity_only:
            total, created = create_bot_users(count=count)
            self.stdout.write(
                self.style.SUCCESS(f"Bot kullanıcılar: toplam {total}, yeni oluşturulan {created}")
            )
            if create_only:
                return

        if not create_only:
            result = run_activity_cycle(questions_per_cycle=questions)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Aktivite: {result['questions_created']} soru, {result['answers_created']} cevap."
                )
            )
