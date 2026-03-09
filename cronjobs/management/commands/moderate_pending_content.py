from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "BadWord + LLM ile bekleyen soru/cevap/yorumları (moderation_status=0) moderasyon sürecinden geçirir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Her model için en fazla kaç kaydın işleneceği.",
        )

    def handle(self, *args, **options):
        from moderation.services import (
            check_text_bad_words,
            llm_moderate,
            save_suggested_bad_words,
            notify_user_moderation_removed,
        )
        from questions.models import Question
        from answers.models import Answer
        from comments.models import Comment
        from blog.models import BlogComment

        limit = options["limit"]
        total = 0

        def moderate_instance(obj, text, rejected_message: str, on_approved=None, on_rejected=None):
            nonlocal total
            text = (text or "").strip()
            if not text:
                # Boş içerik: direkt reddetmek yerine onaylı saymak daha güvenli
                obj.moderation_status = 1
                obj.save(update_fields=["moderation_status"])
                if on_approved:
                    on_approved(obj)
                total += 1
                return

            has_bad, _words = check_text_bad_words(text)
            if has_bad:
                obj.moderation_status = 2
                obj.save(update_fields=["moderation_status"])
                notify_user_moderation_removed(obj.author, rejected_message)
                if on_rejected:
                    on_rejected(obj)
                total += 1
                return

            status, bad_words = llm_moderate(text)
            if status == "RED":
                save_suggested_bad_words(bad_words)
                obj.moderation_status = 2
                obj.save(update_fields=["moderation_status"])
                notify_user_moderation_removed(obj.author, rejected_message)
                if on_rejected:
                    on_rejected(obj)
            else:
                obj.moderation_status = 1
                obj.save(update_fields=["moderation_status"])
                if on_approved:
                    on_approved(obj)
            total += 1

        # Sorular
        pending_questions = Question.objects.filter(
            moderation_status=0,
            is_deleted=False,
        ).order_by("created_at")[:limit]

        for q in pending_questions:
            text = " ".join(
                str(s)
                for s in [
                    q.title or "",
                    q.description or "",
                    q.content or "",
                ]
            )

            def on_question_approved(question_obj):
                # Şimdilik ekstra bir şey yapmıyoruz; gerekirse cache invalidate vb.
                return

            moderate_instance(
                q,
                text,
                rejected_message="Moderatör tarafından sorunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
                on_approved=on_question_approved,
            )

        # Cevaplar
        pending_answers = Answer.objects.filter(
            moderation_status=0,
            is_deleted=False,
        ).select_related("question", "author")[:limit]

        for a in pending_answers:

            def on_answer_status_change(answer_obj):
                from questions.models import Question

                q = answer_obj.question
                # Yalnızca onaylanmış ve silinmemiş cevaplar sayılır
                q.answer_count = q.answers.filter(moderation_status=1, is_deleted=False).count()
                q.save(update_fields=["answer_count"])

            moderate_instance(
                a,
                a.content,
                rejected_message="Moderatör tarafından yorumunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
                on_approved=on_answer_status_change,
                on_rejected=on_answer_status_change,
            )

        # Yorumlar (questions/answers için generic Comment modeli)
        pending_comments = Comment.objects.filter(
            moderation_status=0,
            is_deleted=False,
        ).select_related("author")[:limit]

        for c in pending_comments:
            moderate_instance(
                c,
                c.content,
                rejected_message="Moderatör tarafından yorumunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
            )

        # Blog yorumları
        pending_blog_comments = BlogComment.objects.filter(
            moderation_status=0,
        ).select_related("author")[:limit]

        for bc in pending_blog_comments:
            moderate_instance(
                bc,
                bc.content,
                rejected_message="Moderatör tarafından yorumunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
            )

        self.stdout.write(self.style.SUCCESS(f"Moderation completed. Processed {total} objects."))

