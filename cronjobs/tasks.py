"""
Moderasyon için Celery task'ları. İçerik oluşturulunca kuyruğa alınır,
Celery worker BadWord + LLM ile işler.

Loglama: logger.info ile konsol / LOGGING ayarına göre dosyaya yazılır; DB'ye yazılmaz.
"""
import logging
from celery import shared_task
from django.apps import apps

logger = logging.getLogger(__name__)


@shared_task(name="cronjobs.moderate_content")
def moderate_content_task(model_label, pk):
    """
    Tek bir kayıt için moderasyon çalıştırır.
    model_label: 'questions.Question', 'answers.Answer', 'blog.BlogComment', 'comments.Comment'
    pk: kaydın id'si
    """
    logger.info("Moderation task received: model=%s pk=%s", model_label, pk)
    from moderation.services import run_moderation

    try:
        Model = apps.get_model(model_label)
    except (LookupError, ValueError):
        return {"status": "skip", "reason": "invalid_model"}

    try:
        obj = Model.objects.get(pk=pk)
    except Model.DoesNotExist:
        return {"status": "skip", "reason": "not_found"}

    if getattr(obj, "moderation_status", None) != 0:
        return {"status": "skip", "reason": "already_processed"}

    rejected_message = "Moderatör tarafından içeriğiniz reddedildi. Kurallara aykırı içerik tespit edildi."

    if model_label == "questions.Question":
        pt = getattr(obj, "pending_title", "") or ""
        pd = getattr(obj, "pending_description", "") or ""
        pc = getattr(obj, "pending_content", "") or ""
        if pt or pd or pc:
            text_source = "pending"
            text = " ".join(str(s) for s in [pt, pd, pc])
        else:
            text_source = "live"
            text = " ".join(
                str(s) for s in [getattr(obj, "title", "") or "", getattr(obj, "description", "") or "", getattr(obj, "content", "") or ""]
            )
        logger.info(
            "Moderation question text prepared: model=%s pk=%s source=%s preview=%s",
            model_label,
            pk,
            text_source,
            (text or "")[:200],
        )

        def question_apply_pending(q):
            if getattr(q, "pending_title", None) or getattr(q, "pending_description", None) or getattr(q, "pending_content", None):
                q.title = (q.pending_title or q.title)
                q.description = (q.pending_description or q.description)
                q.content = (q.pending_content or q.content)
                q.pending_title = ""
                q.pending_description = ""
                q.pending_content = ""
                q.save(update_fields=["title", "description", "content", "pending_title", "pending_description", "pending_content"])

        def question_clear_pending(q):
            if getattr(q, "pending_title", None) or getattr(q, "pending_description", None) or getattr(q, "pending_content", None):
                q.pending_title = ""
                q.pending_description = ""
                q.pending_content = ""
                q.save(update_fields=["pending_title", "pending_description", "pending_content"])

        run_moderation(
            obj,
            text,
            "Moderatör tarafından sorunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
            on_approved=question_apply_pending,
            on_rejected=question_clear_pending,
        )

    elif model_label == "answers.Answer":
        pending_text = (getattr(obj, "pending_content", None) or "").strip()
        if pending_text:
            text_source = "pending"
            text = pending_text
        else:
            text_source = "live"
            text = getattr(obj, "content", "") or ""
        logger.info(
            "Moderation answer text prepared: model=%s pk=%s source=%s preview=%s",
            model_label,
            pk,
            text_source,
            (text or "")[:200],
        )

        def update_answer_count(answer_obj):
            from questions.models import Question
            q = answer_obj.question
            q.answer_count = q.answers.filter(moderation_status=1, is_deleted=False).count()
            q.save(update_fields=["answer_count"])

        def answer_apply_pending(a):
            if getattr(a, "pending_content", None):
                a.content = a.pending_content
                a.pending_content = None
                a.save(update_fields=["content", "pending_content"])
            update_answer_count(a)
            # Soru sahibine bildirim sadece moderasyon onayından sonra (cevap kendi sorusuna değilse)
            if a.question.author_id != a.author_id:
                from notifications.services import create_notification
                create_notification(
                    a.question.author,
                    a.author,
                    'answer',
                    f"{a.author.username} soruna cevap yazdı",
                    question=a.question,
                    answer=a,
                )
            try:
                from reputation.badge_service import BadgeService

                BadgeService.on_answer_moderation_approved(a)
            except Exception:
                logger.exception("BadgeService.on_answer_moderation_approved failed for answer %s", getattr(a, "pk", None))

        def answer_clear_pending(a):
            if getattr(a, "pending_content", None):
                a.pending_content = None
                a.save(update_fields=["pending_content"])
            update_answer_count(a)

        run_moderation(
            obj,
            text,
            "Moderatör tarafından yorumunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
            on_approved=answer_apply_pending,
            on_rejected=answer_clear_pending,
        )

    elif model_label == "blog.BlogComment":
        text = getattr(obj, "content", "") or ""
        run_moderation(obj, text, rejected_message)

    elif model_label == "comments.Comment":
        text = getattr(obj, "content", "") or ""
        run_moderation(obj, text, rejected_message)

    return {"status": "ok", "model": model_label, "pk": pk}
