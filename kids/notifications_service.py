"""
Kids bildirimleri: veritabanı kaydı + FCM (KidsFCMDeviceToken).
Ana site User / Notification tablosundan bağımsızdır.
"""
import logging
from django.conf import settings

from notifications.services import deliver_fcm_push_tokens

from .models import (
    KidsAssignment,
    KidsEnrollment,
    KidsFCMDeviceToken,
    KidsNotification,
    KidsSubmission,
    KidsUser,
    KidsUserRole,
)

logger = logging.getLogger(__name__)


def _kids_app_path(*parts: str) -> str:
    """Uygulama rotası; pathPrefix (örn. /kids) hariç — istemci pathPrefix + bu path ile birleştirir."""
    segs = [s.strip("/") for s in parts if s and str(s).strip("/")]
    return "/" + "/".join(segs) if segs else "/"


def kids_notification_relative_path(
    notification_type: str,
    *,
    assignment: KidsAssignment | None = None,
    submission: KidsSubmission | None = None,
) -> str:
    """Next.js: `${pathPrefix}${action_path}` (örn. action_path=/ogrenci/odev/3)."""
    if notification_type == KidsNotification.NotificationType.NEW_ASSIGNMENT and assignment:
        return _kids_app_path("ogrenci", "odev", str(assignment.pk))
    if notification_type == KidsNotification.NotificationType.SUBMISSION_RECEIVED and submission:
        cid = submission.assignment.kids_class_id
        return _kids_app_path("ogretmen", "sinif", str(cid))
    return _kids_app_path("bildirimler")


def kids_notification_absolute_url(
    notification_type: str,
    *,
    assignment: KidsAssignment | None = None,
    submission: KidsSubmission | None = None,
) -> str:
    """Push tıklama: sunucunun bildiği tam Kids kökü + isteğe bağlı URL öneki."""
    base = (getattr(settings, "KIDS_FRONTEND_URL", None) or "").strip().rstrip("/")
    rel = kids_notification_relative_path(
        notification_type, assignment=assignment, submission=submission
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


def create_kids_notification(
    recipient: KidsUser,
    sender: KidsUser | None,
    notification_type: str,
    message: str,
    *,
    assignment: KidsAssignment | None = None,
    submission: KidsSubmission | None = None,
) -> KidsNotification | None:
    if sender is not None and recipient.pk == sender.pk:
        return None
    n = KidsNotification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        message=message,
        assignment=assignment,
        submission=submission,
    )
    tokens = list(
        KidsFCMDeviceToken.objects.filter(kids_user=recipient).values_list("token", flat=True)
    )
    if tokens:
        click_url = kids_notification_absolute_url(
            notification_type, assignment=assignment, submission=submission
        )
        data = {
            "type": notification_type,
            "url": click_url,
            "icon_type": "default",
        }
        if assignment:
            data["kids_assignment_id"] = str(assignment.pk)
        if submission:
            data["kids_submission_id"] = str(submission.pk)
        deliver_fcm_push_tokens(
            tokens,
            title="Marifetli Kids",
            body=message,
            data=data,
            invalidate_token=_kids_push_invalidate,
        )
    return n


def notify_students_new_assignment(assignment_id: int) -> None:
    try:
        assignment = KidsAssignment.objects.select_related("kids_class").get(pk=assignment_id)
    except KidsAssignment.DoesNotExist:
        return
    if not assignment.is_published:
        return
    class_name = assignment.kids_class.name
    student_ids = KidsEnrollment.objects.filter(kids_class_id=assignment.kids_class_id).values_list(
        "student_id", flat=True
    )
    students = KidsUser.objects.filter(pk__in=student_ids, role=KidsUserRole.STUDENT)
    teacher = assignment.kids_class.teacher
    msg = f"Yeni ödev: {assignment.title} ({class_name})"
    for student in students:
        try:
            create_kids_notification(
                student,
                teacher,
                KidsNotification.NotificationType.NEW_ASSIGNMENT,
                msg,
                assignment=assignment,
            )
        except Exception:
            logger.exception("Kids new_assignment notify failed student=%s", student.pk)


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
    teacher = sub.assignment.kids_class.teacher
    student_label = sub.student.full_name or sub.student.email
    msg = f"{student_label} ödevini teslim etti: {sub.assignment.title}"
    try:
        create_kids_notification(
            teacher,
            sub.student,
            KidsNotification.NotificationType.SUBMISSION_RECEIVED,
            msg,
            assignment=sub.assignment,
            submission=sub,
        )
    except Exception:
        logger.exception("Kids submission_received notify failed submission=%s", submission_id)
