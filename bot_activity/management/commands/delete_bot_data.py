"""
Tüm bot kullanıcıları ve onların soruları/cevapları/yorumlarını siler.
Kullanım:
  python manage.py delete_bot_data           # Silmeden önce sayıları gösterir, --yes ile onay gerekir
  python manage.py delete_bot_data --yes    # Onaylamadan siler
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from answers.models import Answer
from questions.models import Question
from comments.models import Comment

User = get_user_model()


class Command(BaseCommand):
    help = "Bot kullanıcıları ile soruları, cevapları ve yorumlarını siler."

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Onay sormadan siler.",
        )

    def handle(self, *args, **options):
        bots = User.objects.filter(is_bot=True)
        n_bots = bots.count()
        if n_bots == 0:
            self.stdout.write(self.style.WARNING("Silinecek bot kullanıcı yok."))
            return

        n_answers = Answer.objects.filter(author__is_bot=True).count()
        n_comments = Comment.objects.filter(author__is_bot=True).count()
        n_questions = Question.objects.filter(author__is_bot=True).count()

        self.stdout.write(
            f"Silinecek: {n_bots} bot, {n_questions} soru, {n_answers} cevap, {n_comments} yorum."
        )
        if not options["yes"]:
            confirm = input("Devam etmek için 'evet' yazın: ")
            if confirm.strip().lower() != "evet":
                self.stdout.write("İptal edildi.")
                return

        # Sıra: önce bot'un yazdığı cevaplar ve yorumlar, sonra bot'un soruları (CASCADE ile o sorulardaki cevaplar da gider), en son bot kullanıcılar
        deleted_answers, _ = Answer.objects.filter(author__is_bot=True).delete()
        deleted_comments, _ = Comment.objects.filter(author__is_bot=True).delete()
        deleted_questions, _ = Question.objects.filter(author__is_bot=True).delete()
        deleted_users, _ = User.objects.filter(is_bot=True).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Silindi: {deleted_users} kullanıcı, {deleted_questions} soru, {deleted_answers} cevap, {deleted_comments} yorum."
            )
        )
