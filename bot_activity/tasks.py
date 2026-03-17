"""
Celery task: bot aktivite döngüsü (soru + cevap).
Beat ile periyodik tetiklenir; BOT_USERS_ENABLED=True ve GEMINI_API_KEY tanımlıysa çalışır.
"""
import logging

from celery import shared_task

from .services import create_bot_users, run_activity_cycle, is_bot_enabled

logger = logging.getLogger(__name__)


@shared_task(name="bot_activity.run_bot_activity")
def run_bot_activity_task():
    """
    Bot kullanıcıları yoksa/eksikse oluşturur, ardından bir tur aktivite çalıştırır
    (kategorilerden rastgele soru açar, botlar cevap yazar).
    Celery Beat ile periyodik çağrılır; günde kaç soru geleceği schedule + BOT_QUESTIONS_PER_RUN ile belirlenir.
    """
    if not is_bot_enabled():
        logger.debug("Bot aktivite atlandı: BOT_USERS_ENABLED veya GEMINI_API_KEY kapalı/eksik.")
        return {"skipped": True, "reason": "bot_disabled"}

    from django.conf import settings

    questions_per_run = getattr(settings, "BOT_QUESTIONS_PER_RUN", 5)
    questions_per_run = max(1, min(questions_per_run, 20))

    # Eksik botları tamamla (zaten 100 varsa no-op)
    total_bots, created_bots = create_bot_users(count=100)
    if created_bots:
        logger.info("Bot aktivite: %d yeni bot oluşturuldu, toplam %d.", created_bots, total_bots)

    result = run_activity_cycle(questions_per_cycle=questions_per_run)
    logger.info(
        "Bot aktivite tamamlandı: %d soru, %d cevap.",
        result["questions_created"],
        result["answers_created"],
    )
    return {
        "skipped": False,
        "bots_created": created_bots,
        "questions_created": result["questions_created"],
        "answers_created": result["answers_created"],
    }
