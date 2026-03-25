"""
Kids bildirimleri: veritabanı kaydı + FCM (KidsFCMDeviceToken).
Ana site User / Notification tablosundan bağımsızdır.
"""
import logging

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from notifications.services import deliver_fcm_push_tokens

from .models import (
    KidsAssignment,
    KidsChallenge,
    KidsChallengeInvite,
    KidsEnrollment,
    KidsFCMDeviceToken,
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
) -> str:
    """Next.js: `${pathPrefix}${action_path}` (örn. action_path=/ogrenci/proje/3)."""
    if notification_type == KidsNotification.NotificationType.NEW_ASSIGNMENT and assignment:
        return _kids_app_path("ogrenci", "proje", str(assignment.pk))
    if notification_type == KidsNotification.NotificationType.SUBMISSION_RECEIVED and submission:
        cid = submission.assignment.kids_class_id
        return _kids_app_path("ogretmen", "sinif", str(cid))
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
    return _kids_app_path("bildirimler")


def kids_notification_absolute_url(
    notification_type: str,
    *,
    assignment: KidsAssignment | None = None,
    submission: KidsSubmission | None = None,
    challenge: KidsChallenge | None = None,
    challenge_invite: KidsChallengeInvite | None = None,
) -> str:
    """Push tıklama: sunucunun bildiği tam Kids kökü + isteğe bağlı URL öneki."""
    base = (getattr(settings, "KIDS_FRONTEND_URL", None) or "").strip().rstrip("/")
    rel = kids_notification_relative_path(
        notification_type,
        assignment=assignment,
        submission=submission,
        challenge=challenge,
        challenge_invite=challenge_invite,
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
    )
    tokens = _fcm_tokens_for_recipient(
        recipient_student=recipient_student,
        recipient_user=recipient_user,
    )
    if tokens:
        click_url = kids_notification_absolute_url(
            notification_type,
            assignment=assignment,
            submission=submission,
            challenge=challenge,
            challenge_invite=challenge_invite,
        )
        try:
            deliver_fcm_push_tokens(
                list(tokens),
                title="Marifetli Kids",
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
        msg = f"Yeni proje: {assignment.title} ({class_name})"
        for student in students:
            try:
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
    msg = f"{student_label} projesini teslim etti: {sub.assignment.title}"
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
