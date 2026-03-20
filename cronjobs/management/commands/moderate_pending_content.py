from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "BadWord + LLM ile bekleyen (moderation_status=0) kayıtları işler. "
        "Normalde background task kullanılır; bu komut toplu/fallback için."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Her model için en fazla kaç kaydın işleneceği.",
        )

    def handle(self, *args, **options):
        from moderation.services import run_moderation
        from questions.models import Question
        from answers.models import Answer
        from comments.models import Comment
        from blog.models import BlogComment

        limit = options["limit"]
        total = 0

        def on_answer_status_change(answer_obj):
            q = answer_obj.question
            q.answer_count = q.answers.filter(moderation_status=1, is_deleted=False).count()
            q.save(update_fields=["answer_count"])
            if answer_obj.moderation_status == 1:
                try:
                    from reputation.badge_service import BadgeService

                    BadgeService.on_answer_moderation_approved(answer_obj)
                except Exception:
                    pass

        # Sorular
        for q in Question.objects.filter(moderation_status=0, is_deleted=False).order_by("created_at")[:limit]:
            text = " ".join(str(s) for s in [q.title or "", q.description or "", q.content or ""])
            run_moderation(q, text, "Moderatör tarafından sorunuz reddedildi. Kurallara aykırı içerik tespit edildi.")
            total += 1

        # Cevaplar
        for a in Answer.objects.filter(moderation_status=0, is_deleted=False).select_related("question")[:limit]:
            run_moderation(
                a,
                a.content or "",
                "Moderatör tarafından yorumunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
                on_approved=on_answer_status_change,
                on_rejected=on_answer_status_change,
            )
            total += 1

        # Yorumlar (generic Comment)
        for c in Comment.objects.filter(moderation_status=0, is_deleted=False)[:limit]:
            run_moderation(c, c.content or "", "Moderatör tarafından yorumunuz reddedildi. Kurallara aykırı içerik tespit edildi.")
            total += 1

        # Blog yorumları
        for bc in BlogComment.objects.filter(moderation_status=0)[:limit]:
            run_moderation(bc, bc.content or "", "Moderatör tarafından yorumunuz reddedildi. Kurallara aykırı içerik tespit edildi.")
            total += 1

        self.stdout.write(self.style.SUCCESS(f"Moderation completed. Processed {total} objects."))

