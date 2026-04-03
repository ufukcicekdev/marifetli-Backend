"""
Kids bildirimleri: veritabanı kaydı + FCM (KidsFCMDeviceToken).
Ana site User / Notification tablosundan bağımsızdır.
"""
import logging

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.i18n_catalog import translate
from core.i18n_resolve import language_for_kids_recipient
from notifications.services import deliver_fcm_push_tokens

from .kg_slots import normalize_kg_slots
from .models import (
    KidsAnnouncement,
    KidsAssignment,
    KidsChallenge,
    KidsChallengeInvite,
    KidsClass,
    KidsConversation,
    KidsEnrollment,
    KidsFCMDeviceToken,
    KidsHomework,
    KidsHomeworkSubmission,
    KidsKindergartenClassDayPlan,
    KidsKindergartenDailyRecord,
    KidsMessage,
    KidsNotification,
    KidsSubmission,
    KidsUser,
    KidsUserRole,
)

logger = logging.getLogger(__name__)
_MainUser = get_user_model()


def _kids_app_path(*parts: str) -> str:
    """Uygulama rotası; pathPrefix (örn. /kids) hariç — istemci pathPrefix + bu path ile birleştirir."""
    segs = [s.strip("/") for s in parts if s and str(s).strip("/")]
    return "/" + "/".join(segs) if segs else "/"


def kids_notification_relative_path(
    notification_type: str,
    *,
    assignment: KidsAssignment | None = None,
    submission: KidsSubmission | None = None,
    challenge: KidsChallenge | None = None,
    challenge_invite: KidsChallengeInvite | None = None,
    conversation: KidsConversation | None = None,
    announcement: KidsAnnouncement | None = None,
    kindergarten_daily_record: KidsKindergartenDailyRecord | None = None,
) -> str:
    """Next.js: `${pathPrefix}${action_path}` (örn. action_path=/ogrenci/proje/3)."""
    if notification_type == KidsNotification.NotificationType.NEW_ASSIGNMENT and assignment:
        return _kids_app_path("ogrenci", "proje", str(assignment.pk))
    if notification_type == KidsNotification.NotificationType.NEW_TEST:
        return _kids_app_path("ogrenci", "testler")
    if notification_type == KidsNotification.NotificationType.SUBMISSION_RECEIVED and submission:
        cid = submission.assignment.kids_class_id
        return _kids_app_path("ogretmen", "sinif", str(cid))
    if notification_type == KidsNotification.NotificationType.NEW_HOMEWORK:
        return _kids_app_path("ogrenci", "odevler")
    if notification_type == KidsNotification.NotificationType.NEW_HOMEWORK_PARENT:
        return _kids_app_path("veli", "panel")
    if notification_type == KidsNotification.NotificationType.HOMEWORK_PARENT_REVIEW_REQUIRED:
        return _kids_app_path("veli", "panel")
    if notification_type == KidsNotification.NotificationType.HOMEWORK_PARENT_APPROVED_FOR_TEACHER:
        return _kids_app_path("ogretmen", "odevler")
    if notification_type == KidsNotification.NotificationType.HOMEWORK_TEACHER_REVIEWED:
        return _kids_app_path("ogrenci", "odevler")
    if notification_type == KidsNotification.NotificationType.CHALLENGE_INVITE and challenge_invite:
        ch = challenge_invite.challenge_id
        if ch:
            return _kids_app_path("ogrenci", "yarismalar", str(ch))
        return _kids_app_path("ogrenci", "yarismalar")
    if notification_type in (
        KidsNotification.NotificationType.CHALLENGE_APPROVED,
        KidsNotification.NotificationType.CHALLENGE_REJECTED,
    ) and challenge:
        return _kids_app_path("ogrenci", "yarismalar", str(challenge.pk))
    if notification_type == KidsNotification.NotificationType.CHALLENGE_PENDING_TEACHER and challenge:
        cid = challenge.kids_class_id
        if cid:
            return _kids_app_path("ogretmen", "sinif", str(cid)) + "?tab=peer"
        return _kids_app_path("bildirimler")
    if notification_type == KidsNotification.NotificationType.CHALLENGE_PENDING_PARENT:
        return _kids_app_path("veli", "yarismalar")
    if notification_type == KidsNotification.NotificationType.NEW_MESSAGE and conversation:
        return _kids_app_path("mesajlar", str(conversation.pk))
    if notification_type == KidsNotification.NotificationType.NEW_ANNOUNCEMENT:
        return _kids_app_path("duyurular")
    if notification_type == KidsNotification.NotificationType.ASSIGNMENT_DUE_SOON and assignment:
        return _kids_app_path("ogrenci", "proje", str(assignment.pk))
    if notification_type == KidsNotification.NotificationType.ASSIGNMENT_LATE_SUBMITTED and submission:
        cid = submission.assignment.kids_class_id
        return _kids_app_path("ogretmen", "sinif", str(cid))
    if notification_type == KidsNotification.NotificationType.ASSIGNMENT_GRADED_WITH_RUBRIC and assignment:
        return _kids_app_path("ogrenci", "proje", str(assignment.pk))
    if notification_type in (
        KidsNotification.NotificationType.KG_CHILD_ARRIVED,
        KidsNotification.NotificationType.KG_END_OF_DAY,
        KidsNotification.NotificationType.KG_MONTHLY_ABSENCE,
    ):
        return _kids_app_path("veli", "cocuklarin-durumu")
    return _kids_app_path("bildirimler")


def kids_notification_absolute_url(
    notification_type: str,
    *,
    assignment: KidsAssignment | None = None,
    submission: KidsSubmission | None = None,
    challenge: KidsChallenge | None = None,
    challenge_invite: KidsChallengeInvite | None = None,
    conversation: KidsConversation | None = None,
    announcement: KidsAnnouncement | None = None,
    kindergarten_daily_record: KidsKindergartenDailyRecord | None = None,
) -> str:
    """Push tıklama: sunucunun bildiği tam Kids kökü + isteğe bağlı URL öneki."""
    base = (getattr(settings, "KIDS_FRONTEND_URL", None) or "").strip().rstrip("/")
    rel = kids_notification_relative_path(
        notification_type,
        assignment=assignment,
        submission=submission,
        challenge=challenge,
        challenge_invite=challenge_invite,
        conversation=conversation,
        announcement=announcement,
        kindergarten_daily_record=kindergarten_daily_record,
    )
    prefix = (getattr(settings, "KIDS_FRONTEND_PATH_PREFIX", None) or "").strip().strip("/")
    if prefix:
        path = f"/{prefix}{rel}" if rel.startswith("/") else f"/{prefix}/{rel}"
    else:
        path = rel if rel.startswith("/") else f"/{rel}"
    return f"{base}{path}" if base else path


def _kids_push_invalidate(token: str) -> None:
    deleted, _ = KidsFCMDeviceToken.objects.filter(token=token).delete()
    if deleted:
        logger.info("FCM: geçersiz Kids token silindi")


def _fcm_tokens_for_recipient(
    *,
    recipient_student: KidsUser | None,
    recipient_user: _MainUser | None,
) -> list[str]:
    if recipient_student:
        return list(
            KidsFCMDeviceToken.objects.filter(kids_user=recipient_student).values_list("token", flat=True)
        )
    if recipient_user:
        return list(KidsFCMDeviceToken.objects.filter(user=recipient_user).values_list("token", flat=True))
    return []


def create_kids_notification(
    *,
    notification_type: str,
    message: str,
    recipient_student: KidsUser | None = None,
    recipient_user: _MainUser | None = None,
    sender_student: KidsUser | None = None,
    sender_user: _MainUser | None = None,
    assignment: KidsAssignment | None = None,
    submission: KidsSubmission | None = None,
    challenge: KidsChallenge | None = None,
    challenge_invite: KidsChallengeInvite | None = None,
    conversation: KidsConversation | None = None,
    message_record: KidsMessage | None = None,
    announcement: KidsAnnouncement | None = None,
    kindergarten_daily_record: KidsKindergartenDailyRecord | None = None,
) -> KidsNotification | None:
    if recipient_student is None and recipient_user is None:
        return None
    if (
        recipient_student
        and sender_student
        and recipient_student.pk == sender_student.pk
    ):
        return None
    if recipient_user and sender_user and recipient_user.pk == sender_user.pk:
        return None
    n = KidsNotification.objects.create(
        recipient_student=recipient_student,
        recipient_user=recipient_user,
        sender_student=sender_student,
        sender_user=sender_user,
        notification_type=notification_type,
        message=message,
        assignment=assignment,
        submission=submission,
        challenge=challenge,
        challenge_invite=challenge_invite,
        conversation=conversation,
        message_record=message_record,
        announcement=announcement,
        kindergarten_daily_record=kindergarten_daily_record,
    )
    tokens = _fcm_tokens_for_recipient(
        recipient_student=recipient_student,
        recipient_user=recipient_user,
    )
    if tokens:
        _fb = None
        if assignment and getattr(assignment, "kids_class", None):
            _fb = getattr(assignment.kids_class, "language", None)
        elif kindergarten_daily_record and getattr(kindergarten_daily_record, "kids_class", None):
            _fb = getattr(kindergarten_daily_record.kids_class, "language", None)
        _lang = language_for_kids_recipient(
            recipient_student=recipient_student,
            recipient_user=recipient_user,
            fallback_lang=_fb,
        )
        click_url = kids_notification_absolute_url(
            notification_type,
            assignment=assignment,
            submission=submission,
            challenge=challenge,
            challenge_invite=challenge_invite,
            conversation=conversation,
            announcement=announcement,
            kindergarten_daily_record=kindergarten_daily_record,
        )
        try:
            deliver_fcm_push_tokens(
                list(tokens),
                title=translate(_lang, "kids.push.app_title"),
                body=message,
                data={"click_url": click_url} if click_url else None,
                invalidate_token=_kids_push_invalidate,
            )
        except Exception:
            logger.exception("Kids FCM push failed")
    return n


def notify_students_new_assignment(assignment_id: int) -> None:
    try:
        assignment = KidsAssignment.objects.select_related("kids_class").get(pk=assignment_id)
    except KidsAssignment.DoesNotExist:
        return
    try:
        if not assignment.is_published:
            return
        if assignment.students_notified_at:
            return
        now = timezone.now()
        if assignment.submission_opens_at and now < assignment.submission_opens_at:
            return

        class_name = assignment.kids_class.name
        student_ids = KidsEnrollment.objects.filter(
            kids_class_id=assignment.kids_class_id
        ).values_list("student_id", flat=True)
        students = KidsUser.objects.filter(pk__in=student_ids, role=KidsUserRole.STUDENT)
        teacher_user = assignment.kids_class.teacher
        for student in students:
            try:
                _lang = language_for_kids_recipient(recipient_student=student, recipient_user=None)
                msg = translate(
                    _lang,
                    "kids.notif.new_assignment",
                    title=assignment.title,
                    class_name=class_name,
                )
                create_kids_notification(
                    recipient_student=student,
                    sender_user=teacher_user,
                    notification_type=KidsNotification.NotificationType.NEW_ASSIGNMENT,
                    message=msg,
                    assignment=assignment,
                )
            except Exception:
                logger.exception("Kids new_assignment notify failed student=%s", student.pk)

        assignment.students_notified_at = now
        assignment.save(update_fields=["students_notified_at", "updated_at"])
    except Exception:
        logger.exception("notify_students_new_assignment failed assignment_id=%s", assignment_id)


def notify_teacher_submission_received(submission_id: int) -> None:
    try:
        sub = KidsSubmission.objects.select_related(
            "assignment",
            "assignment__kids_class",
            "assignment__kids_class__teacher",
            "student",
        ).get(pk=submission_id)
    except KidsSubmission.DoesNotExist:
        return
    teacher_user = sub.assignment.kids_class.teacher
    student_label = sub.student.full_name or sub.student.email
    _lang = language_for_kids_recipient(recipient_student=None, recipient_user=teacher_user)
    msg = translate(
        _lang,
        "kids.notif.submission_received",
        student=student_label,
        title=sub.assignment.title,
    )
    try:
        create_kids_notification(
            recipient_user=teacher_user,
            sender_student=sub.student,
            notification_type=KidsNotification.NotificationType.SUBMISSION_RECEIVED,
            message=msg,
            assignment=sub.assignment,
            submission=sub,
        )
    except Exception:
        logger.exception("Kids submission_received notify failed submission=%s", submission_id)


def notify_students_new_homework(homework_id: int) -> None:
    try:
        homework = KidsHomework.objects.select_related("kids_class", "kids_class__teacher").get(
            pk=homework_id
        )
    except KidsHomework.DoesNotExist:
        return
    if not homework.is_published:
        return
    student_ids = KidsEnrollment.objects.filter(kids_class_id=homework.kids_class_id).values_list(
        "student_id", flat=True
    )
    students = KidsUser.objects.filter(pk__in=student_ids, role=KidsUserRole.STUDENT)
    teacher_user = homework.kids_class.teacher
    class_name = homework.kids_class.name
    parent_children: dict[int, set[str]] = {}
    for student in students:
        try:
            _lang = language_for_kids_recipient(recipient_student=student, recipient_user=None)
            msg = translate(
                _lang,
                "kids.notif.new_homework",
                title=homework.title,
                class_name=class_name,
            )
            create_kids_notification(
                recipient_student=student,
                sender_user=teacher_user,
                notification_type=KidsNotification.NotificationType.NEW_HOMEWORK,
                message=msg,
            )
        except Exception:
            logger.exception("Kids new_homework notify failed student=%s", student.pk)
        parent_id = getattr(student, "parent_account_id", None)
        if parent_id:
            name = (student.full_name or "").strip() or student.email
            parent_children.setdefault(parent_id, set()).add(name)
    if parent_children:
        parents = _MainUser.objects.filter(pk__in=parent_children.keys())
        for parent in parents:
            child_names = sorted(parent_children.get(parent.pk) or [])
            _lang = language_for_kids_recipient(recipient_student=None, recipient_user=parent)
            if len(child_names) == 1:
                parent_msg = translate(
                    _lang,
                    "kids.notif.new_homework_parent_one",
                    child=child_names[0],
                    title=homework.title,
                    class_name=class_name,
                )
            else:
                parent_msg = translate(
                    _lang,
                    "kids.notif.new_homework_parent_multi",
                    title=homework.title,
                    class_name=class_name,
                )
            try:
                create_kids_notification(
                    recipient_user=parent,
                    sender_user=teacher_user,
                    notification_type=KidsNotification.NotificationType.NEW_HOMEWORK_PARENT,
                    message=parent_msg,
                )
            except Exception:
                logger.exception("Kids new_homework parent notify failed parent=%s", parent.pk)


def notify_parent_homework_review_required(submission_id: int) -> None:
    try:
        sub = KidsHomeworkSubmission.objects.select_related(
            "student",
            "homework",
            "homework__kids_class",
        ).get(pk=submission_id)
    except KidsHomeworkSubmission.DoesNotExist:
        return
    parent = sub.student.parent_account
    if not parent:
        return
    if sub.status != KidsHomeworkSubmission.Status.STUDENT_DONE:
        return
    student_label = sub.student.full_name or sub.student.email
    _lang = language_for_kids_recipient(recipient_student=None, recipient_user=parent)
    msg = translate(
        _lang,
        "kids.notif.homework_review_required",
        student=student_label,
        title=sub.homework.title,
    )
    try:
        create_kids_notification(
            recipient_user=parent,
            sender_student=sub.student,
            notification_type=KidsNotification.NotificationType.HOMEWORK_PARENT_REVIEW_REQUIRED,
            message=msg,
        )
    except Exception:
        logger.exception("Kids homework parent review notify failed submission=%s", submission_id)


def notify_teacher_homework_parent_approved(submission_id: int) -> None:
    try:
        sub = KidsHomeworkSubmission.objects.select_related(
            "student",
            "homework",
            "homework__kids_class",
            "homework__kids_class__teacher",
            "parent_reviewed_by",
        ).get(pk=submission_id)
    except KidsHomeworkSubmission.DoesNotExist:
        return
    if sub.status != KidsHomeworkSubmission.Status.TEACHER_APPROVED:
        return
    teacher_user = sub.homework.kids_class.teacher
    student_label = sub.student.full_name or sub.student.email
    _lang = language_for_kids_recipient(recipient_student=None, recipient_user=teacher_user)
    msg = translate(
        _lang,
        "kids.notif.homework_parent_finalized",
        student=student_label,
        title=sub.homework.title,
    )
    try:
        create_kids_notification(
            recipient_user=teacher_user,
            sender_user=sub.parent_reviewed_by,
            notification_type=KidsNotification.NotificationType.HOMEWORK_PARENT_APPROVED_FOR_TEACHER,
            message=msg,
        )
    except Exception:
        logger.exception("Kids homework teacher notify failed submission=%s", submission_id)


def notify_student_homework_teacher_reviewed(submission_id: int) -> None:
    try:
        sub = KidsHomeworkSubmission.objects.select_related(
            "student",
            "homework",
            "homework__kids_class",
            "homework__kids_class__teacher",
            "teacher_reviewed_by",
        ).get(pk=submission_id)
    except KidsHomeworkSubmission.DoesNotExist:
        return
    if sub.status not in (
        KidsHomeworkSubmission.Status.TEACHER_APPROVED,
        KidsHomeworkSubmission.Status.TEACHER_REVISION,
    ):
        return
    teacher = sub.teacher_reviewed_by or sub.homework.kids_class.teacher
    _lang = language_for_kids_recipient(recipient_student=sub.student, recipient_user=None)
    if sub.status == KidsHomeworkSubmission.Status.TEACHER_APPROVED:
        msg = translate(_lang, "kids.notif.homework_teacher_approved", title=sub.homework.title)
    else:
        msg = translate(_lang, "kids.notif.homework_teacher_revision", title=sub.homework.title)
    try:
        create_kids_notification(
            recipient_student=sub.student,
            sender_user=teacher,
            notification_type=KidsNotification.NotificationType.HOMEWORK_TEACHER_REVIEWED,
            message=msg,
        )
    except Exception:
        logger.exception("Kids homework student notify failed submission=%s", submission_id)


def _kg_tri(lang: str, value: bool | None) -> str:
    if value is True:
        return translate(lang, "kids.kg.yes")
    if value is False:
        return translate(lang, "kids.kg.no")
    return translate(lang, "kids.kg.unmarked")


def _kg_format_slots_block(lang: str, slots) -> str | None:
    """Birden fazla öğün/uyku satırı; boşsa None."""
    norm = normalize_kg_slots(slots)
    if not norm:
        return None
    lines = [f"• {s.get('label', '')}: {_kg_tri(lang, s.get('ok'))}" for s in norm]
    return "\n".join(lines) if lines else None


def notify_kindergarten_parent_arrival(record_id: int) -> None:
    try:
        rec = KidsKindergartenDailyRecord.objects.select_related(
            "student", "kids_class", "kids_class__teacher"
        ).get(pk=record_id)
    except KidsKindergartenDailyRecord.DoesNotExist:
        return
    student = rec.student
    parent = getattr(student, "parent_account", None)
    if parent is None:
        return
    plan_row = (
        KidsKindergartenClassDayPlan.objects.filter(
            kids_class_id=rec.kids_class_id, plan_date=rec.record_date
        )
        .only("plan_text")
        .first()
    )
    plan_text = (plan_row.plan_text or "").strip() if plan_row else ""
    child_name = student.full_name or student.email
    lang = language_for_kids_recipient(recipient_user=parent, recipient_student=None)
    if plan_text:
        msg = translate(lang, "kids.notif.kg_arrived_plan", name=child_name, plan=plan_text)
    else:
        msg = translate(lang, "kids.notif.kg_arrived", name=child_name)
    teacher_user = rec.kids_class.teacher
    try:
        create_kids_notification(
            recipient_user=parent,
            sender_user=teacher_user,
            notification_type=KidsNotification.NotificationType.KG_CHILD_ARRIVED,
            message=msg,
            kindergarten_daily_record=rec,
        )
    except Exception:
        logger.exception("notify_kindergarten_parent_arrival failed record=%s", record_id)


def notify_kindergarten_parent_end_of_day(record_id: int) -> None:
    try:
        rec = KidsKindergartenDailyRecord.objects.select_related(
            "student", "kids_class", "kids_class__teacher"
        ).get(pk=record_id)
    except KidsKindergartenDailyRecord.DoesNotExist:
        return
    student = rec.student
    parent = getattr(student, "parent_account", None)
    if parent is None:
        return
    lang = language_for_kids_recipient(recipient_user=parent, recipient_student=None)
    tn = (rec.teacher_day_note or "").strip()
    note_extra = "\n\n" + tn if tn else ""
    meal_detail = _kg_format_slots_block(lang, getattr(rec, "meal_slots", None))
    nap_detail = _kg_format_slots_block(lang, getattr(rec, "nap_slots", None))
    meal_str = meal_detail if meal_detail else _kg_tri(lang, rec.meal_ok)
    nap_str = nap_detail if nap_detail else _kg_tri(lang, rec.nap_ok)
    msg = translate(
        lang,
        "kids.notif.kg_end_of_day",
        name=student.full_name or student.email,
        date=str(rec.record_date),
        present=_kg_tri(lang, rec.present),
        meal=meal_str,
        nap=nap_str,
        note=note_extra,
    )
    teacher_user = rec.kids_class.teacher
    try:
        create_kids_notification(
            recipient_user=parent,
            sender_user=teacher_user,
            notification_type=KidsNotification.NotificationType.KG_END_OF_DAY,
            message=msg,
            kindergarten_daily_record=rec,
        )
    except Exception:
        logger.exception("notify_kindergarten_parent_end_of_day failed record=%s", record_id)


def notify_kindergarten_parent_monthly_absence(
    *,
    student_id: int,
    kids_class_id: int,
    year: int,
    month: int,
    absence_count: int,
) -> None:
    try:
        student = KidsUser.objects.get(pk=student_id, role=KidsUserRole.STUDENT)
    except KidsUser.DoesNotExist:
        return
    kc = KidsClass.objects.filter(pk=kids_class_id).select_related("teacher").first()
    if not kc:
        return
    parent = getattr(student, "parent_account", None)
    if parent is None:
        return
    lang = language_for_kids_recipient(recipient_user=parent, recipient_student=None)
    month_label = f"{year}-{int(month):02d}"
    msg = translate(
        lang,
        "kids.notif.kg_monthly_absence",
        name=student.full_name or student.email,
        month_label=month_label,
        count=absence_count,
    )
    teacher_user = kc.teacher
    try:
        create_kids_notification(
            recipient_user=parent,
            sender_user=teacher_user,
            notification_type=KidsNotification.NotificationType.KG_MONTHLY_ABSENCE,
            message=msg,
            kindergarten_daily_record=None,
        )
    except Exception:
        logger.exception(
            "notify_kindergarten_parent_monthly_absence failed student=%s class=%s",
            student_id,
            kids_class_id,
        )
