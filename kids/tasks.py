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

from kids.models import (
    KidsAssignment,
    KidsAttendanceRecord,
    KidsEnrollment,
    KidsGameSession,
    KidsHomeworkSubmission,
    KidsNotification,
    KidsTestAttempt,
    KidsUser,
    KidsUserRole,
)
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


@shared_task
def weekly_parent_report():
    """
    Her Pazartesi 08:30 çalışır.
    Geçen haftanın (Pazartesi–Pazar) öğrenci istatistiklerini toplar,
    her veliye uygulama içi bildirim + e-posta gönderir.
    """
    from emails.services import EmailService

    today = timezone.localdate()
    # Geçen haftanın başı (Pazartesi) ve sonu (Pazar)
    week_end = today - dt.timedelta(days=today.weekday() + 1)   # geçen Pazar
    week_start = week_end - dt.timedelta(days=6)                # geçen Pazartesi

    week_start_dt = timezone.make_aware(dt.datetime.combine(week_start, dt.time.min))
    week_end_dt = timezone.make_aware(dt.datetime.combine(week_end, dt.time.max))

    # Bağlı velisi olan tüm öğrenciler
    students = KidsUser.objects.filter(
        role=KidsUserRole.STUDENT,
        parent_account__isnull=False,
        is_active=True,
    ).select_related("parent_account")

    for student in students:
        parent = student.parent_account
        if not parent or not parent.email:
            continue
        try:
            hw_count = KidsHomeworkSubmission.objects.filter(
                student=student,
                created_at__range=(week_start_dt, week_end_dt),
            ).count()

            test_attempts = KidsTestAttempt.objects.filter(
                student=student,
                submitted_at__range=(week_start_dt, week_end_dt),
            )
            test_count = test_attempts.count()
            avg_score = None
            if test_count:
                scores = [a.score for a in test_attempts if a.score is not None]
                avg_score = round(sum(scores) / len(scores), 1) if scores else None

            sessions = KidsGameSession.objects.filter(
                student=student,
                status="completed",
                created_at__range=(week_start_dt, week_end_dt),
            )
            game_minutes = sum(
                (s.duration_seconds or 0) for s in sessions
            ) // 60

            attendance_qs = KidsAttendanceRecord.objects.filter(
                student=student,
                date__range=(week_start, week_end),
            )
            absent_days = attendance_qs.filter(status="absent").count()
            present_days = attendance_qs.filter(status="present").count()
            school_days = attendance_qs.count() or 5  # kayıt yoksa 5 varsay

            # Hiç aktivite yoksa bildirim gönderme
            if hw_count == 0 and test_count == 0 and game_minutes == 0:
                continue

            student_name = student.first_name or student.student_login_name or "Öğrenci"

            summary = (
                f"{student_name}: ödev {hw_count}, test {test_count}, oyun {game_minutes} dk"
            )

            # Uygulama içi bildirim (kısa)
            create_kids_notification(
                recipient_user=parent,
                notification_type=KidsNotification.NotificationType.GENERAL,
                message=f"Haftalık özet: {summary}",
            )

            # E-posta (güzel tablo)
            try:
                EmailService.send_weekly_report_email(
                    parent=parent,
                    student_name=student_name,
                    week_start=week_start,
                    week_end=week_end,
                    hw_count=hw_count,
                    test_count=test_count,
                    avg_score=avg_score,
                    game_minutes=game_minutes,
                    present_days=present_days,
                    school_days=school_days,
                    absent_days=absent_days,
                )
            except Exception:
                logger.exception("weekly_parent_report email failed parent=%s student=%s", parent.id, student.id)

        except Exception:
            logger.exception("weekly_parent_report failed student=%s", student.id)
