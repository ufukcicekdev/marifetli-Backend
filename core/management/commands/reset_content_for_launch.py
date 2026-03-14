"""
Blog, sorular, topluluklar ve ilgili yorumları/cevapları siler — canlıda temiz başlangıç için.

Kullanım:
  python manage.py reset_content_for_launch --dry-run  # Sadece sayıları gösterir, silmez
  python manage.py reset_content_for_launch --yes     # Onaylamayı atla ve sil (canlıda bunu kullan)
"""
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Blog yazıları, sorular, topluluklar ve yorumları/cevapları siler (canlı temiz başlangıç)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Sadece silinecek kayıt sayılarını göster, silme.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Onay sormadan sil (script/canlı için).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        yes = options["yes"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — hiçbir şey silinmeyecek.\n"))
        elif not yes:
            self.stdout.write(
                self.style.WARNING(
                    "Bu komut blog, sorular, topluluklar ve yorumları KALICI siler.\n"
                    "Devam etmek için: python manage.py reset_content_for_launch --yes"
                )
            )
            return

        # Model importları (silme sırasına göre bağımlılık var)
        from notifications.models import Notification
        from favorites.models import SavedItem
        from answers.models import Answer, AnswerLike, AnswerReport
        from questions.models import Question, QuestionLike, QuestionView, QuestionReport
        from blog.models import BlogPost, BlogComment, BlogLike
        from communities.models import Community, CommunityMember, CommunityBan, CommunityJoinRequest
        from categories.models import Category

        stats = {}

        # 1) Bildirimler (question, answer, community'ye referans)
        stats["notifications"] = Notification.objects.count()
        if not dry_run:
            Notification.objects.all().delete()

        # 2) Kaydedilenler (SavedItem — Question/BlogPost content type)
        ct_question = ContentType.objects.get(app_label="questions", model="question")
        ct_blog = ContentType.objects.get(app_label="blog", model="blogpost")
        saved_question = SavedItem.objects.filter(content_type=ct_question).count()
        saved_blog = SavedItem.objects.filter(content_type=ct_blog).count()
        stats["saved_items_question"] = saved_question
        stats["saved_items_blog"] = saved_blog
        if not dry_run:
            SavedItem.objects.filter(content_type__in=[ct_question, ct_blog]).delete()

        # 3) Soru cevapları (Answer) — Question.best_answer önce temizlenmeli
        stats["questions_best_answer_cleared"] = Question.objects.exclude(best_answer=None).count()
        if not dry_run:
            Question.objects.update(best_answer=None)

        # 4) Cevap beğeni ve raporlar (Answer silinince CASCADE ile gider; açıkça da silebiliriz)
        stats["answer_likes"] = AnswerLike.objects.count()
        stats["answer_reports"] = AnswerReport.objects.count()
        stats["answers"] = Answer.objects.count()
        if not dry_run:
            Answer.objects.all().delete()

        # 5) Soru beğeni, görüntülenme, raporlar ve sorular
        stats["question_likes"] = QuestionLike.objects.count()
        stats["question_views"] = QuestionView.objects.count()
        stats["question_reports"] = QuestionReport.objects.count()
        stats["questions"] = Question.objects.count()
        if not dry_run:
            Question.objects.all().delete()

        # 6) Blog yorumları ve beğenileri (BlogPost silinince CASCADE; yine de sayalım)
        stats["blog_comments"] = BlogComment.objects.count()
        stats["blog_likes"] = BlogLike.objects.count()
        stats["blog_posts"] = BlogPost.objects.count()
        if not dry_run:
            BlogPost.objects.all().delete()

        # 7) Topluluk üyeleri, yasaklar, katılım talepleri ve topluluklar
        stats["community_members"] = CommunityMember.objects.count()
        stats["community_bans"] = CommunityBan.objects.count()
        stats["community_join_requests"] = CommunityJoinRequest.objects.count()
        stats["communities"] = Community.objects.count()
        if not dry_run:
            Community.objects.all().delete()

        # 8) Kategori question_count sıfırla
        stats["categories_updated"] = Category.objects.exclude(question_count=0).count()
        if not dry_run:
            Category.objects.update(question_count=0)

        # Özet
        self.stdout.write("\n--- Özet ---")
        for key, value in stats.items():
            self.stdout.write(f"  {key}: {value}")
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run bitti. Silmek için --dry-run olmadan çalıştırın."))
        else:
            self.stdout.write(self.style.SUCCESS("\nİçerik sıfırlandı. Canlıda temiz başlangıç hazır."))
