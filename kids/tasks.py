"""
Kids Celery görevleri (planlanmış proje penceresi bildirimi).
"""

import logging

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from kids.models import KidsAssignment
from kids.notifications_service import notify_students_new_assignment

logger = logging.getLogger(__name__)


@shared_task
def notify_kids_assignment_windows_opened():
    """
    Teslim başlangıcı gelmiş ama henüz öğrencilere bildirilmemiş projeler.
    `notify_students_new_assignment` idempotent (students_notified_at).
    """
    now = timezone.now()
    ids = list(
        KidsAssignment.objects.filter(
            is_published=True,
            students_notified_at__isnull=True,
        )
        .filter(Q(submission_opens_at__isnull=True) | Q(submission_opens_at__lte=now))
        .values_list("id", flat=True)[:500]
    )
    for aid in ids:
        try:
            notify_students_new_assignment(aid)
        except Exception:
            logger.exception("notify_kids_assignment_windows_opened failed assignment_id=%s", aid)
