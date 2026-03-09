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
        text = " ".join(
            str(s) for s in [getattr(obj, "title", "") or "", getattr(obj, "description", "") or "", getattr(obj, "content", "") or ""]
        )
        run_moderation(
            obj,
            text,
            "Moderatör tarafından sorunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
        )

    elif model_label == "answers.Answer":
        text = getattr(obj, "content", "") or ""

        def update_answer_count(answer_obj):
            from questions.models import Question
            q = answer_obj.question
            q.answer_count = q.answers.filter(moderation_status=1, is_deleted=False).count()
            q.save(update_fields=["answer_count"])

        run_moderation(
            obj,
            text,
            "Moderatör tarafından yorumunuz reddedildi. Kurallara aykırı içerik tespit edildi.",
            on_approved=update_answer_count,
            on_rejected=update_answer_count,
        )

    elif model_label == "blog.BlogComment":
        text = getattr(obj, "content", "") or ""
        run_moderation(obj, text, rejected_message)

    elif model_label == "comments.Comment":
        text = getattr(obj, "content", "") or ""
        run_moderation(obj, text, rejected_message)

    return {"status": "ok", "model": model_label, "pk": pk}
