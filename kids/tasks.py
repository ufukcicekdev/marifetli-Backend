"""
Kids Celery görevleri (planlanmış proje penceresi bildirimi).
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from kids.models import KidsAssignment, KidsEnrollment, KidsNotification, KidsUser, KidsUserRole
from kids.notifications_service import create_kids_notification, notify_students_new_assignment

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


@shared_task
def notify_kids_assignments_due_soon(hours_before: int = 24):
    """Son teslime yaklaşan ödevler için öğrenci/veli hatırlatmaları."""
    now = timezone.now()
    upper = now + timedelta(hours=max(1, int(hours_before or 24)))
    qs = KidsAssignment.objects.filter(
        is_published=True,
        due_soon_notified_at__isnull=True,
        submission_closes_at__isnull=False,
        submission_closes_at__gt=now,
        submission_closes_at__lte=upper,
    )[:500]
    for assignment in qs:
        try:
            student_ids = KidsEnrollment.objects.filter(kids_class_id=assignment.kids_class_id).values_list(
                "student_id", flat=True
            )
            students = KidsUser.objects.filter(pk__in=student_ids, role=KidsUserRole.STUDENT)
            for student in students:
                create_kids_notification(
                    recipient_student=student,
                    sender_user=assignment.kids_class.teacher,
                    notification_type=KidsNotification.NotificationType.ASSIGNMENT_DUE_SOON,
                    message=f"Son teslim yaklaşıyor: {assignment.title}",
                    assignment=assignment,
                )
                if student.parent_account_id:
                    create_kids_notification(
                        recipient_user=student.parent_account,
                        sender_user=assignment.kids_class.teacher,
                        notification_type=KidsNotification.NotificationType.ASSIGNMENT_DUE_SOON,
                        message=f"{student.full_name or student.email} için son teslim yaklaşıyor: {assignment.title}",
                        assignment=assignment,
                    )
            assignment.due_soon_notified_at = now
            assignment.save(update_fields=["due_soon_notified_at", "updated_at"])
        except Exception:
            logger.exception("notify_kids_assignments_due_soon failed assignment_id=%s", assignment.id)
