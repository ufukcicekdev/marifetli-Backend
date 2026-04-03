"""
Kids Celery görevleri (planlanmış proje penceresi bildirimi).
"""

import datetime as dt
import logging
from calendar import monthrange
from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from core.i18n_catalog import translate
from core.i18n_resolve import language_for_kids_recipient

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
                lang_s = language_for_kids_recipient(recipient_student=student)
                create_kids_notification(
                    recipient_student=student,
                    sender_user=assignment.kids_class.teacher,
                    notification_type=KidsNotification.NotificationType.ASSIGNMENT_DUE_SOON,
                    message=translate(lang_s, "kids.notif.due_soon", title=assignment.title),
                    assignment=assignment,
                )
                if student.parent_account_id:
                    lang_p = language_for_kids_recipient(recipient_user=student.parent_account)
                    create_kids_notification(
                        recipient_user=student.parent_account,
                        sender_user=assignment.kids_class.teacher,
                        notification_type=KidsNotification.NotificationType.ASSIGNMENT_DUE_SOON,
                        message=translate(
                            lang_p,
                            "kids.notif.due_soon_parent",
                            student=student.full_name or student.email,
                            title=assignment.title,
                        ),
                        assignment=assignment,
                    )
            assignment.due_soon_notified_at = now
            assignment.save(update_fields=["due_soon_notified_at", "updated_at"])
        except Exception:
            logger.exception("notify_kids_assignments_due_soon failed assignment_id=%s", assignment.id)


@shared_task
def kindergarten_monthly_absence_digest():
    """
    Bir önceki ayda `present=False` ile işaretlenen anaokulu / anasınıfı günleri için veli bildirimi.
    Her ayın 1'inde Beat ile tetiklenir; (öğrenci, sınıf, yıl, ay) başına bir kez loglanır.
    """
    from kids.models import (
        KidsClass,
        KidsClassKind,
        KidsEnrollment,
        KidsKindergartenDailyRecord,
        KidsKindergartenMonthlyReportLog,
    )
    from kids.notifications_service import notify_kindergarten_parent_monthly_absence

    today = timezone.localdate()
    if today.month == 1:
        y, m = today.year - 1, 12
    else:
        y, m = today.year, today.month - 1
    first = dt.date(y, m, 1)
    last = dt.date(y, m, monthrange(y, m)[1])

    for kc in KidsClass.objects.filter(
        class_kind__in=(KidsClassKind.KINDERGARTEN, KidsClassKind.ANASINIFI),
    ).only("id"):
        for student_id in (
            KidsEnrollment.objects.filter(kids_class=kc)
            .values_list("student_id", flat=True)
            .distinct()
        ):
            if KidsKindergartenMonthlyReportLog.objects.filter(
                student_id=student_id, kids_class=kc, year=y, month=m
            ).exists():
                continue
            cnt = KidsKindergartenDailyRecord.objects.filter(
                kids_class=kc,
                student_id=student_id,
                record_date__gte=first,
                record_date__lte=last,
                present=False,
            ).count()
            if cnt > 0:
                try:
                    notify_kindergarten_parent_monthly_absence(
                        student_id=student_id,
                        kids_class_id=kc.pk,
                        year=y,
                        month=m,
                        absence_count=cnt,
                    )
                except Exception:
                    logger.exception(
                        "kindergarten_monthly_absence_digest notify failed sid=%s cid=%s",
                        student_id,
                        kc.pk,
                    )
            try:
                KidsKindergartenMonthlyReportLog.objects.create(
                    student_id=student_id,
                    kids_class=kc,
                    year=y,
                    month=m,
                    absence_count=cnt,
                )
            except Exception:
                logger.exception(
                    "kindergarten_monthly_absence_digest log failed sid=%s cid=%s",
                    student_id,
                    kc.pk,
                )
