import logging
import re
import secrets
import unicodedata
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from emails.services import EmailService
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .badges import (
    MAX_TEACHER_PICKS_PER_ASSIGNMENT,
    apply_teacher_pick,
    build_student_roadmap,
    sync_growth_milestone_badges,
    try_award_badge,
    try_award_first_submit_badge,
)
from .auth_utils import (
    is_kids_admin_user,
    is_kids_student_user,
    is_main_user,
    may_access_kids_with_main_jwt,
)
from .authentication import KidsJWTAuthentication, KidsOrMainSiteStaffJWTAuthentication
from .jwt_utils import kids_decode_token, kids_encode_token
from .main_site_bridge import provision_kids_parent_user, unique_username_from_email
from .models import (
    KidsAssignment,
    KidsChallengeMember,
    KidsClass,
    KidsEnrollment,
    KidsFCMDeviceToken,
    KidsFreestylePost,
    KidsGame,
    KidsGameProgress,
    KidsGameSession,
    KidsInvite,
    KidsNotification,
    KidsParentGamePolicy,
    KidsSchool,
    KidsSchoolTeacher,
    KidsSchoolYearProfile,
    KidsSubmission,
    KidsUser,
    KidsUserBadge,
    KidsUserRole,
    MebSchoolDirectory,
)
from .notifications_service import notify_students_new_assignment, notify_teacher_submission_received
from .permissions import IsKidsAdmin, IsKidsParent, IsKidsTeacherOrAdmin
from .meb_directory import split_line_full_location
from .school_access import enrolled_distinct_student_count_for_school_year, schools_queryset_for_main_user
from .turkey_il_plaka import (
    il_name_to_plaka_int,
    il_plaka_db_variants,
    province_name_from_il_plaka_raw,
)
from users.models import KidsPortalRole
from users.models import User as MainUser
from users.utils import generate_verification_token

from .serializers import (
    _absolute_media_url,
    KidsAcceptInviteFamilySerializer,
    KidsAcceptInviteLegacySerializer,
    KidsClassInviteLinkSerializer,
    KidsAssignmentSerializer,
    KidsAdminAssignSchoolTeacherSerializer,
    KidsAdminSchoolCreateSerializer,
    KidsClassSerializer,
    KidsEnrollmentSerializer,
    KidsFreestylePostSerializer,
    KidsInviteCreateSerializer,
    KidsInviteSerializer,
    KidsGameSerializer,
    KidsGameSessionCompleteSerializer,
    KidsGameSessionSerializer,
    KidsGameSessionStartSerializer,
    KidsGameProgressSerializer,
    KidsNotificationSerializer,
    KidsParentGamePolicySerializer,
    KidsSchoolSerializer,
    KidsSchoolYearProfileWriteSerializer,
    KidsSubmissionHighlightSerializer,
    KidsSubmissionReviewSerializer,
    KidsSubmissionSerializer,
    KidsTeacherSubmissionSerializer,
    KidsUserProfileUpdateSerializer,
    KidsUserSerializer,
    kids_user_growth_stage,
)

logger = logging.getLogger(__name__)


def _kids_password_reset_abs_url(token: str) -> str:
    base = (getattr(settings, "KIDS_FRONTEND_URL", None) or "").strip().rstrip("/")
    prefix = (getattr(settings, "KIDS_FRONTEND_PATH_PREFIX", None) or "").strip().strip("/")
    tail = f"sifre-sifirla/{token}"
    if prefix:
        path = f"/{prefix}/{tail}"
    else:
        path = f"/{tail}"
    return f"{base}{path}" if base else path


def _kids_login_abs_url(tab: str | None = None) -> str:
    base = (getattr(settings, "KIDS_FRONTEND_URL", None) or "").strip().rstrip("/")
    prefix = (getattr(settings, "KIDS_FRONTEND_PATH_PREFIX", None) or "").strip().strip("/")
    root = f"/{prefix}" if prefix else ""
    slug = tab or "1"
    path = f"{root}?giris={slug}"
    return f"{base}{path}" if base else path


def _random_temp_password(length: int = 12) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%*-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _send_kids_teacher_welcome_email(
    *,
    to_email: str,
    first_name: str,
    temp_password: str,
) -> tuple[bool, str | None]:
    login_url = _kids_login_abs_url("ogretmen")
    reset_hint_url = _kids_login_abs_url("ogretmen")
    sent = EmailService.send_kids_teacher_welcome_email(
        to_email=to_email,
        first_name=first_name,
        temp_password=temp_password,
        login_url=login_url,
        reset_hint_url=reset_hint_url,
    )
    if sent and getattr(sent, "status", None) == "sent":
        return True, None
    return False, getattr(sent, "error_message", None) or "E-posta gönderilemedi"


def _kids_user_payload(user: KidsUser, request) -> dict:
    return KidsUserSerializer(user, context={"request": request}).data


def _map_user_to_api_role(u: MainUser) -> str:
    if u.is_superuser or u.is_staff:
        return "admin"
    r = (u.kids_portal_role or "").strip()
    if r == KidsPortalRole.KIDS_ADMIN:
        return "admin"
    if r == KidsPortalRole.TEACHER:
        return "teacher"
    if r == KidsPortalRole.PARENT:
        return "parent"
    return "teacher"


def _account_kids_payload(u: MainUser, request) -> dict:
    linked = None
    if (u.kids_portal_role or "").strip() == KidsPortalRole.PARENT:
        qs = KidsUser.objects.filter(parent_account=u, is_active=True).order_by(
            "first_name", "last_name", "id"
        )
        linked = [
            {
                "id": s.id,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "student_login_name": s.student_login_name,
            }
            for s in qs
        ]
    return {
        "id": u.id,
        "email": u.email,
        "first_name": u.first_name or "",
        "last_name": u.last_name or "",
        "role": _map_user_to_api_role(u),
        "created_at": u.date_joined.isoformat() if hasattr(u, "date_joined") and u.date_joined else "",
        "profile_picture": None,
        "growth_points": 0,
        "growth_stage": None,
        "student_login_name": None,
        "phone": None,
        "linked_students": linked,
    }


def _issue_login_tokens(actor: KidsUser | MainUser, raw_password: str) -> tuple[str, str, str]:
    if isinstance(actor, KidsUser):
        return (
            kids_encode_token(actor.id, token_type="access"),
            kids_encode_token(actor.id, token_type="refresh"),
            "kids",
        )
    ref = RefreshToken.for_user(actor)
    return str(ref.access_token), str(ref), "main_site"


def _parent_child_overview_dict(student: KidsUser) -> dict:
    """Veli paneli: çocuğun sınıfları, rozetleri, proje ve yarışma özeti (salt okunur)."""
    class_ids = list(
        KidsEnrollment.objects.filter(student=student).values_list("kids_class_id", flat=True)
    )
    classes_data = []
    if class_ids:
        for kc in KidsClass.objects.filter(id__in=class_ids).select_related("school").order_by("name"):
            classes_data.append(
                {
                    "id": kc.id,
                    "name": kc.name,
                    "school_name": kc.school.name if kc.school else "",
                }
            )

    badges_raw = list(
        KidsUserBadge.objects.filter(student=student)
        .order_by("-earned_at")[:24]
        .values("key", "label", "earned_at")
    )
    for b in badges_raw:
        ea = b.get("earned_at")
        if ea is not None:
            b["earned_at"] = ea.isoformat()

    challenges_data = []
    for m in (
        KidsChallengeMember.objects.filter(student=student)
        .select_related("challenge", "challenge__kids_class")
        .order_by("-joined_at")[:12]
    ):
        ch = m.challenge
        kc = ch.kids_class
        challenges_data.append(
            {
                "title": ch.title,
                "status": ch.status,
                "class_name": kc.name if kc else "Serbest",
                "peer_scope": getattr(ch, "peer_scope", "class_peer"),
                "is_initiator": m.is_initiator,
            }
        )

    assignments_out = []
    now = timezone.now()
    if class_ids:
        assignments_qs = (
            KidsAssignment.objects.filter(
                kids_class_id__in=class_ids,
                is_published=True,
            )
            .filter(Q(submission_opens_at__isnull=True) | Q(submission_opens_at__lte=now))
            .select_related("kids_class")
            .order_by(F("submission_closes_at").desc(nulls_last=True), "-id")[:30]
        )
        aid_list = [a.id for a in assignments_qs]
        sub_by_assignment: dict[int, list] = {}
        if aid_list:
            subs = KidsSubmission.objects.filter(
                student=student, assignment_id__in=aid_list
            ).order_by("assignment_id", "round_number", "-id")
            for sub in subs:
                sub_by_assignment.setdefault(sub.assignment_id, []).append(sub)
        for a in assignments_qs:
            subs = sub_by_assignment.get(a.id, [])
            rounds_submitted = len({s.round_number for s in subs})
            awaiting_feedback = any(s.teacher_reviewed_at is None for s in subs) if subs else False
            last_note = None
            reviewed = [s for s in subs if s.teacher_reviewed_at]
            if reviewed:
                last_r = max(reviewed, key=lambda s: s.teacher_reviewed_at or timezone.now())
                note = (last_r.teacher_note_to_student or "").strip()
                if note:
                    last_note = note[:280]
            closes = a.submission_closes_at.isoformat() if a.submission_closes_at else None
            assignments_out.append(
                {
                    "id": a.id,
                    "title": a.title,
                    "class_name": a.kids_class.name,
                    "submission_closes_at": closes,
                    "submission_rounds": a.submission_rounds,
                    "rounds_submitted": rounds_submitted,
                    "has_submissions": bool(subs),
                    "awaiting_teacher_feedback": awaiting_feedback,
                    "teacher_feedback_preview": last_note,
                    "got_teacher_star": any(s.is_teacher_pick for s in subs),
                }
            )

    pending_parent_actions: list[dict] = []
    # İleride: yükleme onayı vb. { "type": "...", "title": "...", "ref_id": ... }

    return {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "student_login_name": student.student_login_name,
        "growth_points": int(student.growth_points or 0),
        "growth_stage": kids_user_growth_stage(student),
        "classes": classes_data,
        "badges": badges_raw,
        "assignments_recent": assignments_out,
        "challenges": challenges_data,
        "pending_parent_actions": pending_parent_actions,
    }


def _ascii_slug_part(s: str) -> str:
    t = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return (t[:20] if t else "ogrenci")


def _generate_unique_student_login_name(first: str, last: str) -> str:
    for _ in range(80):
        suf = uuid.uuid4().hex[:4]
        base = f"{_ascii_slug_part(first)}_{_ascii_slug_part(last)}".strip("_") or "ogrenci"
        base = base[:28]
        cand = f"{base}_{suf}"[:40]
        if not KidsUser.objects.filter(student_login_name__iexact=cand).exists():
            return cand
    return f"{_ascii_slug_part(first)}_{uuid.uuid4().hex}"[:40]


def _invite_email_normalized(invite: KidsInvite, data: dict) -> str | None:
    if invite.is_class_link:
        email_raw = (data.get("email") or "").strip()
        return email_raw.lower() if email_raw else None
    return (invite.parent_email or "").strip().lower() or None


def _school_distinct_enrolled_student_count(school_id: int) -> int:
    return (
        KidsEnrollment.objects.filter(kids_class__school_id=school_id)
        .values("student_id")
        .distinct()
        .count()
    )


def _school_demo_window_active(school: KidsSchool) -> bool:
    if school.lifecycle_stage != KidsSchool.LifecycleStage.DEMO:
        return True
    if not school.demo_start_at or not school.demo_end_at:
        return True
    today = timezone.localdate()
    return school.demo_start_at <= today <= school.demo_end_at


def _school_capacity_remaining(school: KidsSchool) -> int:
    current = _school_distinct_enrolled_student_count(school.id)
    return max(int(school.student_user_cap or 0) - current, 0)


def _school_enrollment_block_reason(school: KidsSchool, seats_needed: int) -> str | None:
    if seats_needed <= 0:
        return None
    if not _school_demo_window_active(school):
        return "Demo süresi dışında öğrenci kaydı açılamaz."
    remaining = _school_capacity_remaining(school)
    if remaining < seats_needed:
        return (
            f"Okul öğrenci limiti dolu veya yetersiz. Kalan kapasite: {remaining}, "
            f"istenen: {seats_needed}."
        )
    return None


def _accept_invite_legacy(request, invite: KidsInvite, data: dict) -> Response:
    if not invite or not invite.is_valid():
        return Response(
            {"detail": "Davet geçersiz veya süresi dolmuş."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    email_norm = _invite_email_normalized(invite, data)
    if not email_norm:
        return Response(
            {"detail": "Öğrenci e-postası gerekli."}
            if invite.is_class_link
            else {"detail": "Davet geçersiz."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    existing = KidsUser.objects.filter(email__iexact=email_norm).first()
    if existing:
        if existing.role != KidsUserRole.STUDENT:
            return Response(
                {"detail": "Bu e-posta başka bir rol ile kayıtlı."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not existing.check_password(data["password"]):
            return Response(
                {"detail": "Şifre hatalı."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if KidsEnrollment.objects.filter(
            kids_class=invite.kids_class, student=existing
        ).exists():
            return Response(
                {"detail": "Bu sınıfa zaten kayıtlısınız. Giriş yapın."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        school = KidsSchool.objects.filter(pk=invite.kids_class.school_id).first()
        needs_new_school_seat = not KidsEnrollment.objects.filter(
            kids_class__school_id=invite.kids_class.school_id,
            student=existing,
        ).exists()
        if school:
            reason = _school_enrollment_block_reason(
                school, seats_needed=1 if needs_new_school_seat else 0
            )
            if reason:
                return Response(
                    {"detail": reason},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        KidsEnrollment.objects.get_or_create(
            kids_class=invite.kids_class, student=existing
        )
        if not invite.is_class_link:
            invite.used_at = timezone.now()
            invite.save(update_fields=["used_at"])
        access = kids_encode_token(existing.id, token_type="access")
        refresh = kids_encode_token(existing.id, token_type="refresh")
        return Response(
            {
                "access": access,
                "refresh": refresh,
                "token_kind": "kids",
                "user": _kids_user_payload(existing, request),
                "enrolled_existing": True,
            },
            status=status.HTTP_200_OK,
        )
    student = KidsUser(
        email=email_norm,
        first_name=data["first_name"],
        last_name=data["last_name"],
        role=KidsUserRole.STUDENT,
    )
    school = KidsSchool.objects.filter(pk=invite.kids_class.school_id).first()
    if school:
        reason = _school_enrollment_block_reason(school, seats_needed=1)
        if reason:
            return Response({"detail": reason}, status=status.HTTP_400_BAD_REQUEST)
    student.set_password(data["password"])
    student.save()
    KidsEnrollment.objects.get_or_create(kids_class=invite.kids_class, student=student)
    if not invite.is_class_link:
        invite.used_at = timezone.now()
        invite.save(update_fields=["used_at"])
    access = kids_encode_token(student.id, token_type="access")
    refresh = kids_encode_token(student.id, token_type="refresh")
    return Response(
        {
            "access": access,
            "refresh": refresh,
            "token_kind": "kids",
            "user": _kids_user_payload(student, request),
        },
        status=status.HTTP_201_CREATED,
    )


def _accept_invite_family(request, invite: KidsInvite, data: dict) -> Response:
    if not invite or not invite.is_valid():
        return Response(
            {"detail": "Davet geçersiz veya süresi dolmuş."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    parent_email_norm = _invite_email_normalized(invite, data)
    if not parent_email_norm:
        return Response(
            {"detail": "Veli e-postası gerekli."}
            if invite.is_class_link
            else {"detail": "Davet geçersiz."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    with transaction.atomic():
        school = (
            KidsSchool.objects.select_for_update()
            .filter(pk=invite.kids_class.school_id)
            .first()
        )
        if school:
            reason = _school_enrollment_block_reason(
                school, seats_needed=len(data.get("children") or [])
            )
            if reason:
                return Response(
                    {"detail": reason},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        existing_main = MainUser.objects.select_for_update().filter(email__iexact=parent_email_norm).first()
        if existing_main:
            if not existing_main.check_password(data["parent_password"]):
                return Response(
                    {"detail": "Veli şifresi hatalı."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            r = (existing_main.kids_portal_role or "").strip()
            if r == KidsPortalRole.TEACHER:
                return Response(
                    {
                        "detail": "Bu e-posta Kids öğretmen hesabı. Veli kaydı için farklı bir e-posta kullanın."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            existing_main.kids_portal_role = KidsPortalRole.PARENT
            existing_main.first_name = data["parent_first_name"].strip()[:150]
            existing_main.last_name = data["parent_last_name"].strip()[:150]
            existing_main.save(
                update_fields=["kids_portal_role", "first_name", "last_name", "updated_at"]
            )
            parent = existing_main
        else:
            try:
                parent = provision_kids_parent_user(
                    email=parent_email_norm,
                    first_name=data["parent_first_name"].strip(),
                    last_name=data["parent_last_name"].strip(),
                    phone="",
                    raw_password=data["parent_password"],
                )
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        students = []
        created_students = []
        for child in (data.get("children") or []):
            internal_email = f"{uuid.uuid4().hex}@student.kids.internal"
            login_name = _generate_unique_student_login_name(
                child["first_name"], child["last_name"]
            )
            student = KidsUser(
                email=internal_email,
                first_name=child["first_name"].strip(),
                last_name=child["last_name"].strip(),
                role=KidsUserRole.STUDENT,
                parent_account=parent,
                student_login_name=login_name,
            )
            student.set_password(child["password"])
            student.save()
            KidsEnrollment.objects.get_or_create(kids_class=invite.kids_class, student=student)
            students.append(student)
            created_students.append(
                {
                    "id": student.id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "student_login_name": login_name,
                }
            )

    if not invite.is_class_link:
        invite.used_at = timezone.now()
        invite.save(update_fields=["used_at"])

    primary_student = students[0]
    ref = RefreshToken.for_user(parent)
    access = str(ref.access_token)
    refresh = str(ref)
    return Response(
        {
            "access": access,
            "refresh": refresh,
            "token_kind": "main_site",
            "user": _account_kids_payload(parent, request),
            "student_login_name": primary_student.student_login_name,
            "created_children": created_students,
            "parent_email": parent_email_norm,
            "flow": "family",
        },
        status=status.HTTP_201_CREATED,
    )


_MAX_PROFILE_PHOTO_BYTES = 2 * 1024 * 1024
_ALLOWED_PROFILE_PHOTO_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
_ALLOWED_SUBMISSION_IMAGE_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def _max_submission_image_bytes() -> int:
    mb = max(1, int(getattr(settings, "KIDS_SUBMISSION_IMAGE_MAX_MB", 25)))
    return mb * 1024 * 1024

# Öğretmen artık görsel üst sınırı seçmez; her teslimde teknik üst sınır (tek görsel).
KIDS_MAX_IMAGES_PER_SUBMISSION = 1


def _steps_image_urls_from_payload(payload):
    if not isinstance(payload, dict):
        return None
    raw = payload.get("image_urls")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    out = []
    for u in raw:
        if not isinstance(u, str):
            return None
        s = u.strip()
        if s:
            out.append(s)
    return out


def _valid_public_http_url(url: str) -> bool:
    if len(url) > 2048:
        return False
    lu = url.lower()
    return lu.startswith("https://") or lu.startswith("http://")


def _assignment_teacher_review_allowed(assignment) -> bool:
    """Değerlendirme, son teslim zamanı geçtikten sonra (veya eski projelerde tarih yoksa)."""
    now = timezone.now()
    if not assignment.submission_closes_at:
        return True
    return now > assignment.submission_closes_at


def _growth_points_for_first_review(valid: bool, positive: bool | None) -> int:
    if valid:
        if positive is True:
            return 3
        if positive is False:
            return 2
        return 0
    return 1


def _student_grade_level(student: KidsUser) -> int:
    """MVP: öğrencinin sınıf adına göre 1-2 seviyesi; bulunamazsa 1."""
    cls = (
        KidsClass.objects.filter(enrollments__student=student)
        .only("name")
        .order_by("-id")
        .first()
    )
    if not cls or not cls.name:
        return 1
    m = re.match(r"^\s*(\d{1,2})", cls.name)
    if not m:
        return 1
    try:
        g = int(m.group(1))
    except (TypeError, ValueError):
        return 1
    if g < 1:
        return 1
    if g > 2:
        return 2
    return g


def _minutes_played_today(student: KidsUser) -> int:
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    rows = KidsGameSession.objects.filter(
        student=student,
        status=KidsGameSession.SessionStatus.COMPLETED,
        started_at__gte=start,
        started_at__lt=end,
    ).values_list("duration_seconds", flat=True)
    total_seconds = sum(int(v or 0) for v in rows)
    return total_seconds // 60


def _is_now_in_allowed_window(now_local, start_t, end_t) -> bool:
    if not start_t or not end_t:
        return True
    cur = now_local.time()
    # Aynı gün penceresi: 18:00-20:00, geceyi aşan: 22:00-07:00.
    if start_t <= end_t:
        return start_t <= cur <= end_t
    return cur >= start_t or cur <= end_t


def _game_policy_error(student: KidsUser, game: KidsGame) -> str | None:
    pol = getattr(student, "game_policy", None)
    if not pol:
        return None
    blocked = pol.blocked_game_ids or []
    if game.id in blocked:
        return "Bu oyun veli kontrolünde geçici olarak kapalı."
    now_local = timezone.localtime()
    if not _is_now_in_allowed_window(now_local, pol.allowed_start_time, pol.allowed_end_time):
        return "Bu saatte oyun oynayamazsın. Veli saat aralığını kontrol et."
    played_min = _minutes_played_today(student)
    if played_min >= int(pol.daily_minutes_limit or 0):
        return "Günlük oyun süresi doldu. Yarın tekrar deneyebilirsin."
    return None


def _apply_game_rewards(student: KidsUser, session: KidsGameSession) -> None:
    if session.status != KidsGameSession.SessionStatus.COMPLETED:
        return
    progress = int(session.progress_percent or 0)
    score = int(session.score or 0)
    delta = 0
    if progress >= 80:
        delta += 2
    elif progress >= 50:
        delta += 1
    if score >= 80:
        delta += 1
    if delta > 0:
        KidsUser.objects.filter(pk=student.id).update(growth_points=F("growth_points") + delta)
    # Oyun tabanlı rozetler (MVP).
    completed_count = KidsGameSession.objects.filter(
        student=student,
        status=KidsGameSession.SessionStatus.COMPLETED,
    ).count()
    if completed_count >= 1:
        try_award_badge(student.id, "game_first_complete", "İlk oyun tamamlandı")
    if completed_count >= 5:
        try_award_badge(student.id, "game_five_complete", "5 oyun tamamlandı")
    sync_growth_milestone_badges(student.id)


def _daily_quest_score_target(difficulty: str) -> int:
    if difficulty == KidsGame.Difficulty.HARD:
        return 90
    if difficulty == KidsGame.Difficulty.MEDIUM:
        return 70
    return 50


def _assignment_submission_window_error(assignment) -> str | None:
    """Tarih penceresi dışında teslim string hatası; None = devam. Eski projeler (tarih yok) serbest."""
    now = timezone.now()
    if assignment.submission_opens_at and now < assignment.submission_opens_at:
        return "Teslim dönemi henüz başlamadı."
    if assignment.submission_closes_at and now > assignment.submission_closes_at:
        return "Teslim süresi doldu."
    return None


def _assignment_visible_to_students(assignment) -> bool:
    """Yayında ve (başlangıç yok veya başlangıç geçti) — öğrenci paneli / teslim öncesi kontrol."""
    if not assignment.is_published:
        return False
    now = timezone.now()
    if assignment.submission_opens_at and now < assignment.submission_opens_at:
        return False
    return True


def _assignment_editable_as_planned(assignment) -> bool:
    """Öğrenci panelinde henüz görünmüyorsa tam düzenleme (planlanmış veya yayından kalkmış)."""
    if not assignment.is_published:
        return True
    now = timezone.now()
    if assignment.submission_opens_at and now < assignment.submission_opens_at:
        return True
    return False


def _validate_kids_submission_for_assignment(assignment, kind, steps_payload, video_url: str):
    ri, rv = assignment.require_image, assignment.require_video
    is_video = kind == KidsSubmission.SubmissionKind.VIDEO
    is_steps = kind == KidsSubmission.SubmissionKind.STEPS
    vtrim = (video_url or "").strip()
    if is_video:
        if not rv:
            return "Bu proje için video teslimi kabul edilmiyor."
        if not vtrim:
            return "Video bağlantısı gerekli."
    if is_steps:
        if rv and not ri:
            return "Bu proje yalnızca video ile teslim alınır."
        if ri:
            imgs = _steps_image_urls_from_payload(steps_payload)
            if imgs is None:
                return "Görseller geçersiz formatta."
            mx = KIDS_MAX_IMAGES_PER_SUBMISSION
            if len(imgs) < 1:
                return f"En az 1 görsel ekleyin (en fazla {mx})."
            if len(imgs) > mx:
                return f"En fazla {mx} görsel yükleyebilirsiniz."
            for u in imgs:
                if not _valid_public_http_url(u):
                    return "Her görsel geçerli bir http(s) adresi olmalıdır."
    return None


class KidsAuthenticatedMixin:
    authentication_classes = [KidsJWTAuthentication]


class KidsLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = (request.data.get("login") or request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        login_is_email = "@" in raw

        student = None
        if raw:
            student = KidsUser.objects.filter(email__iexact=raw).first()
            if not student and not login_is_email:
                student = KidsUser.objects.filter(student_login_name__iexact=raw).first()

        if student:
            if student.is_active and student.check_password(password):
                access, refresh, token_kind = _issue_login_tokens(student, password)
                return Response(
                    {
                        "access": access,
                        "refresh": refresh,
                        "token_kind": token_kind,
                        "user": _kids_user_payload(student, request),
                    }
                )
            return Response(
                {"detail": "Geçersiz e-posta veya şifre."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not raw or not login_is_email:
            return Response(
                {"detail": "Geçersiz e-posta veya şifre."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        main = MainUser.objects.filter(email__iexact=raw, is_active=True).first()
        if (
            not main
            or getattr(main, "is_deactivated", False)
            or not main.check_password(password)
        ):
            return Response(
                {"detail": "Geçersiz e-posta veya şifre."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not may_access_kids_with_main_jwt(main):
            return Response(
                {"detail": "Bu hesapla Kids bölümüne giriş yetkiniz yok."},
                status=status.HTTP_403_FORBIDDEN,
            )
        access, refresh, token_kind = _issue_login_tokens(main, password)
        return Response(
            {
                "access": access,
                "refresh": refresh,
                "token_kind": token_kind,
                "user": _account_kids_payload(main, request),
            }
        )


class KidsTokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.data.get("refresh") or ""
        payload = kids_decode_token(raw)
        if payload and payload.get("typ") == "refresh":
            try:
                uid = int(payload["sub"])
            except (KeyError, ValueError):
                return Response(
                    {"detail": "Geçersiz token."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not KidsUser.objects.filter(pk=uid, is_active=True).exists():
                return Response(
                    {"detail": "Kullanıcı bulunamadı."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            access = kids_encode_token(uid, token_type="access")
            return Response({"access": access})

        ser = TokenRefreshSerializer(data={"refresh": raw})
        if not ser.is_valid():
            return Response(
                {"detail": "Geçersiz veya süresi dolmuş yenileme jetonu."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(dict(ser.validated_data))


_KIDS_PW_RESET_MSG = (
    "Bu e-posta adresiyle kayıtlı bir Marifetli Kids hesabı varsa, şifre sıfırlama bağlantısı "
    "gönderilir. Gelen kutunuzu ve istenmeyen klasörünüzü kontrol edin."
)


class KidsPasswordResetRequestView(APIView):
    """Kids kullanıcıları (öğrenci/öğretmen) için şifre sıfırlama isteği."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        if not email:
            return Response(
                {"detail": "E-posta adresi gerekli."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = KidsUser.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return Response({"detail": _KIDS_PW_RESET_MSG})
        token = generate_verification_token()
        user.password_reset_token = token
        user.password_reset_token_expiry = timezone.now() + timedelta(hours=1)
        user.save(
            update_fields=["password_reset_token", "password_reset_token_expiry", "updated_at"]
        )
        reset_url = _kids_password_reset_abs_url(token)
        try:
            sent = EmailService.send_kids_password_reset_email(user, token, reset_url)
            if sent is None or getattr(sent, "status", None) == "failed":
                logger.error("Kids şifre sıfırlama e-postası gönderilemedi: %s", email)
                return Response(
                    {"detail": "E-posta gönderilemedi; bir süre sonra tekrar deneyin."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        except Exception:
            logger.exception("Kids şifre sıfırlama e-postası hatası: %s", email)
            return Response(
                {"detail": "E-posta gönderilemedi; bir süre sonra tekrar deneyin."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"detail": _KIDS_PW_RESET_MSG})


class KidsPasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        new_password = request.data.get("new_password") or ""
        if not token or not new_password:
            return Response(
                {"detail": "Token ve yeni şifre gerekli."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 8:
            return Response(
                {"detail": "Şifre en az 8 karakter olmalıdır."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = KidsUser.objects.filter(
            password_reset_token=token,
            password_reset_token_expiry__gt=timezone.now(),
            is_active=True,
        ).first()
        if not user:
            return Response(
                {"detail": "Bağlantı geçersiz veya süresi dolmuş. Yeni bir şifre sıfırlama isteği gönderin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expiry = None
        user.save(
            update_fields=["password", "password_reset_token", "password_reset_token_expiry", "updated_at"]
        )
        return Response({"detail": "Şifreniz güncellendi. Yeni şifrenizle giriş yapabilirsiniz."})


class KidsParentSwitchStudentView(KidsAuthenticatedMixin, APIView):
    """Veli oturumu: kendi doğrulanmış hesabıyla bağlı çocuğun JWT'sine geçiş (e-posta/kullanıcı adı gerekmez)."""

    permission_classes = [IsAuthenticated, IsKidsParent]

    def post(self, request):
        raw = request.data.get("student_id")
        try:
            sid = int(raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Geçerli öğrenci seçilmedi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        parent = request.user
        student = KidsUser.objects.filter(
            pk=sid,
            role=KidsUserRole.STUDENT,
            parent_account_id=parent.id,
            is_active=True,
        ).first()
        if not student:
            return Response(
                {"detail": "Bu çocuk hesabına erişim yok veya bulunamadı."},
                status=status.HTTP_404_NOT_FOUND,
            )
        access = kids_encode_token(student.id, token_type="access")
        refresh = kids_encode_token(student.id, token_type="refresh")
        return Response(
            {
                "access": access,
                "refresh": refresh,
                "user": _kids_user_payload(student, request),
            }
        )


class KidsParentChildrenOverviewView(KidsAuthenticatedMixin, APIView):
    """Veli paneli: çocukların başarı ve proje özeti; `pending_parent_actions` ileride onay kuyruğu için."""

    permission_classes = [IsAuthenticated, IsKidsParent]

    def get(self, request):
        children = request.user.kids_children_accounts.filter(
            role=KidsUserRole.STUDENT, is_active=True
        ).order_by("first_name", "last_name", "id")
        return Response({"children": [_parent_child_overview_dict(s) for s in children]})


class KidsParentGamePolicyDetailView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsParent]

    def get(self, request, student_id: int):
        student = KidsUser.objects.filter(
            pk=student_id,
            parent_account=request.user,
            role=KidsUserRole.STUDENT,
            is_active=True,
        ).first()
        if not student:
            return Response(status=status.HTTP_404_NOT_FOUND)
        policy, _ = KidsParentGamePolicy.objects.get_or_create(student=student)
        return Response(KidsParentGamePolicySerializer(policy).data)

    def put(self, request, student_id: int):
        student = KidsUser.objects.filter(
            pk=student_id,
            parent_account=request.user,
            role=KidsUserRole.STUDENT,
            is_active=True,
        ).first()
        if not student:
            return Response(status=status.HTTP_404_NOT_FOUND)
        policy, _ = KidsParentGamePolicy.objects.get_or_create(student=student)
        ser = KidsParentGamePolicySerializer(policy, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(KidsParentGamePolicySerializer(policy).data)


class KidsParentGamesListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsParent]

    def get(self, request):
        raw = request.query_params.get("student_id")
        student = None
        if raw and str(raw).isdigit():
            student = KidsUser.objects.filter(
                pk=int(raw),
                parent_account=request.user,
                role=KidsUserRole.STUDENT,
                is_active=True,
            ).first()
        if student is None:
            student = (
                request.user.kids_children_accounts.filter(
                    role=KidsUserRole.STUDENT,
                    is_active=True,
                )
                .order_by("id")
                .first()
            )
        if student is None:
            return Response({"games": []})
        grade = _student_grade_level(student)
        qs = KidsGame.objects.filter(
            is_active=True,
            min_grade__lte=grade,
            max_grade__gte=grade,
        ).order_by("sort_order", "title", "id")
        today = timezone.localdate()
        progress_map = {
            p.game_id: p
            for p in KidsGameProgress.objects.filter(student=student, game_id__in=[g.id for g in qs])
        }
        items = []
        for game in qs:
            p = progress_map.get(game.id)
            difficulty = p.current_difficulty if p else KidsGame.Difficulty.EASY
            target = _daily_quest_score_target(difficulty)
            items.append(
                {
                    **KidsGameSerializer(game).data,
                    "progress": {
                        "current_difficulty": difficulty,
                        "streak_count": int(getattr(p, "streak_count", 0) or 0),
                        "best_score": int(getattr(p, "best_score", 0) or 0),
                        "daily_quest_completed_today": bool(
                            p and p.daily_quest_completed_on == today
                        ),
                        "daily_quest_target_score": int(target),
                    },
                }
            )
        return Response(
            {
                "student_id": student.id,
                "grade_level": grade,
                "games": items,
            }
        )


class KidsMeView(KidsAuthenticatedMixin, APIView):
    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        if isinstance(u, MainUser):
            return Response(_account_kids_payload(u, request))
        return Response(_kids_user_payload(u, request))

    def patch(self, request):
        u = request.user
        if isinstance(u, MainUser):
            fn = (request.data.get("first_name") or "").strip()
            ln = (request.data.get("last_name") or "").strip()
            if fn:
                u.first_name = fn[:150]
            if ln:
                u.last_name = ln[:150]
            u.save(update_fields=["first_name", "last_name", "updated_at"])
            return Response(_account_kids_payload(u, request))
        ser = KidsUserProfileUpdateSerializer(u, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(_kids_user_payload(u, request))


class KidsAdminTeacherListCreateView(KidsAuthenticatedMixin, APIView):
    """Admin paneli: öğretmen listele / öğretmen oluştur (rastgele şifre + e-posta)."""

    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def get(self, request):
        qs = (
            MainUser.objects.filter(kids_portal_role=KidsPortalRole.TEACHER)
            .only("id", "email", "first_name", "last_name", "is_active", "created_at")
            .order_by("-created_at")
        )
        rows = [
            {
                "id": t.id,
                "email": t.email,
                "first_name": t.first_name,
                "last_name": t.last_name,
                "is_active": t.is_active,
                "created_at": t.created_at,
            }
            for t in qs
        ]
        return Response({"teachers": rows})

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        first_name = (request.data.get("first_name") or "").strip()
        last_name = (request.data.get("last_name") or "").strip()
        if not email:
            return Response({"detail": "E-posta zorunlu."}, status=status.HTTP_400_BAD_REQUEST)
        if KidsUser.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "Bu e-posta bir öğrenci hesabında kullanılıyor; öğretmen için farklı e-posta seçin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if MainUser.objects.filter(email__iexact=email).exists():
            return Response(
                {
                    "detail": "Bu e-posta Marifetli ana sitede kayıtlı. Öğretmen eklemek için hesaba "
                    "`kids_portal_role=teacher` atayın ve kullanıcıyı bilgilendirin veya farklı e-posta kullanın."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        school_ids = request.data.get("school_ids")
        if school_ids is not None:
            if not isinstance(school_ids, list):
                return Response(
                    {"detail": "school_ids bir tam sayı listesi olmalıdır."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            for sid in school_ids:
                try:
                    sid_int = int(sid)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": "Geçersiz okul kimliği."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if not KidsSchool.objects.filter(pk=sid_int).exists():
                    return Response(
                        {"detail": f"Okul bulunamadı (id={sid_int})."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        temp_password = _random_temp_password()
        with transaction.atomic():
            teacher = MainUser.objects.create_user(
                username=unique_username_from_email(email),
                email=email,
                password=temp_password,
                first_name=first_name[:150],
                last_name=last_name[:150],
                kids_portal_role=KidsPortalRole.TEACHER,
            )
            if school_ids is not None:
                for sid in school_ids:
                    sid_int = int(sid)
                    KidsSchoolTeacher.objects.update_or_create(
                        school_id=sid_int,
                        user_id=teacher.id,
                        defaults={"is_active": True},
                    )
        sent_ok, err = _send_kids_teacher_welcome_email(
            to_email=email,
            first_name=teacher.first_name,
            temp_password=temp_password,
        )
        return Response(
            {
                "teacher": {
                    "id": teacher.id,
                    "email": teacher.email,
                    "first_name": teacher.first_name or "",
                    "last_name": teacher.last_name or "",
                    "is_active": teacher.is_active,
                    "created_at": teacher.created_at,
                },
                "email_sent": sent_ok,
                "email_error": err,
                # SMTP kapalı kurulumlarda adminin kullanıcıya manuel iletebilmesi için fallback.
                "temporary_password": None if sent_ok else temp_password,
            },
            status=status.HTTP_201_CREATED,
        )


class KidsAdminTeacherDetailPatchView(KidsAuthenticatedMixin, APIView):
    """Admin: öğretmen hesabını etkin / pasif yap."""

    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def patch(self, request, pk: int):
        is_active = request.data.get("is_active")
        if not isinstance(is_active, bool):
            return Response(
                {"detail": "is_active alanı boolean olmalıdır."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        teacher = MainUser.objects.filter(pk=pk, kids_portal_role=KidsPortalRole.TEACHER).first()
        if not teacher:
            return Response({"detail": "Öğretmen bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        teacher.is_active = is_active
        teacher.save(update_fields=["is_active"])
        return Response(
            {
                "teacher": {
                    "id": teacher.id,
                    "email": teacher.email,
                    "first_name": teacher.first_name or "",
                    "last_name": teacher.last_name or "",
                    "is_active": teacher.is_active,
                    "created_at": teacher.created_at,
                }
            }
        )


class KidsAdminSchoolListCreateView(KidsAuthenticatedMixin, APIView):
    """Yönetim: okul listesi / oluşturma (yıllık kota ile)."""

    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def get(self, request):
        qs = (
            KidsSchool.objects.all()
            .prefetch_related("year_profiles", "school_teachers__user")
            .order_by("name", "-id")
        )
        return Response({"schools": [_admin_school_detail_payload(s) for s in qs]})

    def post(self, request):
        ser = KidsAdminSchoolCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        year_profiles = vd.get("year_profiles") or []
        with transaction.atomic():
            school = KidsSchool.objects.create(
                teacher=None,
                name=vd["name"].strip(),
                province=(vd.get("province") or "").strip(),
                district=(vd.get("district") or "").strip(),
                neighborhood=(vd.get("neighborhood") or "").strip(),
                lifecycle_stage=vd.get("lifecycle_stage") or KidsSchool.LifecycleStage.DEMO,
                demo_start_at=vd.get("demo_start_at"),
                demo_end_at=vd.get("demo_end_at"),
                student_user_cap=int(vd.get("student_user_cap") or 0),
            )
            for yp in year_profiles:
                w = KidsSchoolYearProfileWriteSerializer(data=yp, context={"school": school})
                w.is_valid(raise_exception=True)
                wvd = w.validated_data
                KidsSchoolYearProfile.objects.create(
                    school=school,
                    academic_year=wvd["academic_year"],
                    contracted_student_count=int(wvd.get("contracted_student_count") or 0),
                    notes=(wvd.get("notes") or "").strip(),
                )
        school = (
            KidsSchool.objects.prefetch_related("year_profiles", "school_teachers__user")
            .filter(pk=school.pk)
            .first()
        )
        return Response(_admin_school_detail_payload(school), status=status.HTTP_201_CREATED)


class KidsAdminSchoolDetailView(KidsAuthenticatedMixin, APIView):
    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def get(self, request, pk: int):
        school = (
            KidsSchool.objects.prefetch_related("year_profiles", "school_teachers__user")
            .filter(pk=pk)
            .first()
        )
        if not school:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_admin_school_detail_payload(school))

    def patch(self, request, pk: int):
        school = KidsSchool.objects.filter(pk=pk).first()
        if not school:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsSchoolSerializer(school, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        school = (
            KidsSchool.objects.prefetch_related("year_profiles", "school_teachers__user")
            .filter(pk=pk)
            .first()
        )
        return Response(_admin_school_detail_payload(school))

    def delete(self, request, pk: int):
        school = KidsSchool.objects.filter(pk=pk).first()
        if not school:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if school.kids_classes.exists():
            return Response(
                {
                    "detail": "Bu okula bağlı sınıflar var. Önce sınıfları taşıyın veya silin.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        school.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KidsAdminSchoolYearProfileListCreateView(KidsAuthenticatedMixin, APIView):
    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def post(self, request, school_pk: int):
        school = KidsSchool.objects.filter(pk=school_pk).first()
        if not school:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsSchoolYearProfileWriteSerializer(data=request.data, context={"school": school})
        ser.is_valid(raise_exception=True)
        wvd = ser.validated_data
        p = KidsSchoolYearProfile.objects.create(
            school=school,
            academic_year=wvd["academic_year"],
            contracted_student_count=int(wvd.get("contracted_student_count") or 0),
            notes=(wvd.get("notes") or "").strip(),
        )
        return Response(
            {
                "id": p.id,
                "academic_year": p.academic_year,
                "contracted_student_count": p.contracted_student_count,
                "enrolled_student_count": enrolled_distinct_student_count_for_school_year(
                    school.pk, p.academic_year
                ),
                "notes": p.notes or "",
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            },
            status=status.HTTP_201_CREATED,
        )


class KidsAdminSchoolYearProfileDetailView(KidsAuthenticatedMixin, APIView):
    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def patch(self, request, pk: int):
        p = KidsSchoolYearProfile.objects.select_related("school").filter(pk=pk).first()
        if not p:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsSchoolYearProfileWriteSerializer(
            p,
            data=request.data,
            partial=True,
            context={"school": p.school},
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        p.refresh_from_db()
        return Response(
            {
                "id": p.id,
                "academic_year": p.academic_year,
                "contracted_student_count": p.contracted_student_count,
                "enrolled_student_count": enrolled_distinct_student_count_for_school_year(
                    p.school_id, p.academic_year
                ),
                "notes": p.notes or "",
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
        )

    def delete(self, request, pk: int):
        p = KidsSchoolYearProfile.objects.filter(pk=pk).first()
        if not p:
            return Response(status=status.HTTP_404_NOT_FOUND)
        p.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KidsAdminSchoolTeacherListCreateView(KidsAuthenticatedMixin, APIView):
    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def post(self, request, school_pk: int):
        school = KidsSchool.objects.filter(pk=school_pk).first()
        if not school:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsAdminAssignSchoolTeacherSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tid = ser.validated_data["teacher_user_id"]
        teacher = MainUser.objects.filter(pk=tid, kids_portal_role=KidsPortalRole.TEACHER).first()
        if not teacher:
            return Response(
                {"detail": "Bu kimlikte bir öğretmen hesabı yok."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        KidsSchoolTeacher.objects.update_or_create(
            school_id=school.pk,
            user_id=teacher.id,
            defaults={"is_active": True},
        )
        school = (
            KidsSchool.objects.prefetch_related("year_profiles", "school_teachers__user")
            .filter(pk=school.pk)
            .first()
        )
        return Response(_admin_school_detail_payload(school), status=status.HTTP_201_CREATED)


class KidsAdminSchoolTeacherRemoveView(KidsAuthenticatedMixin, APIView):
    authentication_classes = [KidsOrMainSiteStaffJWTAuthentication]
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def delete(self, request, school_pk: int, teacher_user_id: int):
        school = KidsSchool.objects.filter(pk=school_pk).first()
        if not school:
            return Response(status=status.HTTP_404_NOT_FOUND)
        KidsSchoolTeacher.objects.filter(school_id=school_pk, user_id=teacher_user_id).delete()
        if school.teacher_id == teacher_user_id:
            KidsSchool.objects.filter(pk=school_pk).update(teacher_id=None)
        school = (
            KidsSchool.objects.prefetch_related("year_profiles", "school_teachers__user")
            .filter(pk=school_pk)
            .first()
        )
        return Response(_admin_school_detail_payload(school))


class KidsAppConfigView(KidsAuthenticatedMixin, APIView):
    """Öğretmen paneli için güvenli özellik bayrakları (.env)."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request):
        return Response(
            {
                "invite_email_enabled": getattr(settings, "KIDS_INVITE_EMAIL_ENABLED", True),
                "assignment_video_enabled": getattr(
                    settings, "KIDS_ASSIGNMENT_VIDEO_ENABLED", True
                ),
            }
        )


class KidsProfilePhotoView(KidsAuthenticatedMixin, APIView):
    """multipart: alan adı `photo` — JPEG, PNG veya WebP, en fazla 2 MB."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        f = request.FILES.get("photo") or request.FILES.get("profile_picture")
        if not f:
            return Response(
                {"detail": "Fotoğraf dosyası gerekli (photo)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if f.size > _MAX_PROFILE_PHOTO_BYTES:
            return Response(
                {"detail": "Dosya en fazla 2 MB olabilir."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ctype = (getattr(f, "content_type", "") or "").lower()
        if ctype not in _ALLOWED_PROFILE_PHOTO_TYPES:
            return Response(
                {"detail": "Yalnızca JPEG, PNG veya WebP yükleyebilirsiniz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        u = request.user
        if isinstance(u, MainUser):
            u.profile_picture = f
            u.save(update_fields=["profile_picture", "updated_at"])
            return Response(_account_kids_payload(u, request))
        u.profile_picture = f
        u.save(update_fields=["profile_picture", "updated_at"])
        return Response(_kids_user_payload(u, request))


class KidsStudentSubmissionImageUploadView(KidsAuthenticatedMixin, APIView):
    """Öğrenci proje görseli: multipart alan `image` — JPEG, PNG veya WebP (üst sınır: settings.KIDS_SUBMISSION_IMAGE_MAX_MB)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        f = request.FILES.get("image")
        if not f:
            return Response(
                {"detail": "Görsel dosyası gerekli (image)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        max_b = _max_submission_image_bytes()
        if f.size > max_b:
            mb = max_b // (1024 * 1024)
            return Response(
                {"detail": f"Görsel çok büyük (en fazla {mb} MB)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ctype = (getattr(f, "content_type", "") or "").lower()
        if ctype not in _ALLOWED_PROFILE_PHOTO_TYPES:
            return Response(
                {"detail": "Yalnızca JPEG, PNG veya WebP yükleyebilirsiniz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ext = Path(f.name or "").suffix.lower()
        if ext not in _ALLOWED_SUBMISSION_IMAGE_EXT:
            ext = ".jpg" if "jpeg" in ctype else ".png" if "png" in ctype else ".webp"
        name = f"kids_submission_images/{uuid.uuid4().hex}{ext}"
        path = default_storage.save(name, f)
        rel = default_storage.url(path)
        return Response({"url": _absolute_media_url(request, rel)})


class KidsInvitePreviewView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        from uuid import UUID

        raw = (request.query_params.get("token") or "").strip()
        try:
            tid = UUID(str(raw))
        except (ValueError, TypeError, AttributeError):
            return Response({"detail": "Geçersiz davet."}, status=status.HTTP_400_BAD_REQUEST)
        invite = (
            KidsInvite.objects.select_related("kids_class__school", "kids_class__teacher")
            .filter(token=tid)
            .first()
        )
        if not invite or not invite.is_valid():
            return Response(
                {"detail": "Davet geçersiz veya süresi dolmuş."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        kc = invite.kids_class
        teacher = kc.teacher
        td = f"{(teacher.first_name or '').strip()} {(teacher.last_name or '').strip()}".strip() or (
            teacher.email or ""
        )
        school = kc.school
        return Response(
            {
                "class_name": kc.name,
                "class_description": (kc.description or "")[:300],
                "teacher_display": td,
                "school_name": school.name if school else "",
                "requires_parent_email": invite.is_class_link,
                "requires_student_email": invite.is_class_link,
                "expires_at": invite.expires_at.isoformat(),
            }
        )


class KidsAcceptInviteView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        body = request.data
        # Veli+çocuk ailesi her zaman parent_password içerir; eski tek-öğrenci akışı göndermez.
        # Önceki kod ayrıca child_first_name şart koşuyordu; yalnızca `children` dizisi gelince
        # yanlışlıkla legacy serializer seçiliyordu (kök first_name/last_name/password hatası).
        is_family = bool(body.get("parent_password"))
        if is_family:
            ser = KidsAcceptInviteFamilySerializer(data=body)
        else:
            ser = KidsAcceptInviteLegacySerializer(data=body)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        invite = KidsInvite.objects.select_related("kids_class").filter(token=data["token"]).first()
        if is_family:
            return _accept_invite_family(request, invite, data)
        return _accept_invite_legacy(request, invite, data)


class KidsClassInviteLinkCreateView(KidsAuthenticatedMixin, APIView):
    """Sınıfa özel, paylaşılabilir çok kullanımlı davet linki (e-posta zorunlu değil)."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def post(self, request, class_id):
        from .invite_email import kids_invite_signup_url

        ser = KidsClassInviteLinkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        days = ser.validated_data["expires_days"]
        kids_class = KidsClass.objects.filter(pk=class_id, teacher=request.user).first()
        if not kids_class:
            return Response(
                {"detail": "Sınıf bulunamadı veya yetkiniz yok."},
                status=status.HTTP_404_NOT_FOUND,
            )
        invite = KidsInvite.objects.create(
            kids_class=kids_class,
            parent_email="",
            is_class_link=True,
            created_by=request.user,
            expires_at=timezone.now() + timedelta(days=days),
        )
        url = kids_invite_signup_url(invite.token)
        return Response(
            {
                "invite": KidsInviteSerializer(invite).data,
                "signup_url": url,
                "expires_days": days,
            },
            status=status.HTTP_201_CREATED,
        )


class KidsClassListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request):
        qs = KidsClass.objects.filter(teacher=request.user).select_related("school", "teacher")
        return Response(KidsClassSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request):
        ser = KidsClassSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        kids_class = ser.save(teacher=request.user)
        kids_class = KidsClass.objects.select_related("school", "teacher").get(pk=kids_class.pk)
        return Response(
            KidsClassSerializer(kids_class, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class KidsClassDetailView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get_object(self, request, pk):
        return (
            KidsClass.objects.filter(pk=pk, teacher=request.user)
            .select_related("school", "teacher")
            .first()
        )

    def get(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(KidsClassSerializer(obj, context={"request": request}).data)

    def patch(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsClassSerializer(obj, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        obj = self.get_object(request, pk)
        return Response(KidsClassSerializer(obj, context={"request": request}).data)

    def delete(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _admin_school_detail_payload(school: KidsSchool) -> dict:
    enrolled_distinct_student_count = _school_distinct_enrolled_student_count(school.id)
    profiles = []
    for p in school.year_profiles.all().order_by("academic_year"):
        profiles.append(
            {
                "id": p.id,
                "academic_year": p.academic_year,
                "contracted_student_count": p.contracted_student_count,
                "enrolled_student_count": enrolled_distinct_student_count_for_school_year(
                    school.pk, p.academic_year
                ),
                "notes": p.notes or "",
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
        )
    teachers = []
    for m in school.school_teachers.filter(is_active=True).select_related("user"):
        u = m.user
        teachers.append(
            {
                "id": u.id,
                "email": u.email,
                "first_name": u.first_name or "",
                "last_name": u.last_name or "",
                "joined_at": m.joined_at,
            }
        )
    base = KidsSchoolSerializer(school).data
    return {
        **base,
        "year_profiles": profiles,
        "teachers": teachers,
        "enrolled_distinct_student_count": enrolled_distinct_student_count,
        "capacity_remaining": max(int(school.student_user_cap or 0) - enrolled_distinct_student_count, 0),
        "demo_is_active": _school_demo_window_active(school),
    }


class KidsSchoolListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request):
        qs = schools_queryset_for_main_user(request.user)
        return Response(KidsSchoolSerializer(qs, many=True).data)

    def post(self, request):
        if not is_kids_admin_user(request.user):
            return Response(
                {
                    "detail": "Okul kaydı yalnızca yönetim panelinden yapılır. "
                    "Lütfen yönetim ile iletişime geçin veya yönetim hesabıyla giriş yapın.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = KidsSchoolSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        school = ser.save(teacher=None)
        return Response(KidsSchoolSerializer(school).data, status=status.HTTP_201_CREATED)


class KidsSchoolDetailView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get_object(self, request, pk):
        return schools_queryset_for_main_user(request.user).filter(pk=pk).first()

    def get(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(KidsSchoolSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(request, pk)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsSchoolSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        obj.refresh_from_db()
        return Response(KidsSchoolSerializer(obj).data)

    def delete(self, request, pk):
        if not is_kids_admin_user(request.user):
            return Response(
                {"detail": "Okul silme yalnızca yönetim içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        obj = schools_queryset_for_main_user(request.user).filter(pk=pk).first()
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if obj.kids_classes.exists():
            return Response(
                {
                    "detail": "Bu okula bağlı sınıflar var. Önce sınıfları başka okula taşıyın veya sınıfları silin.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KidsEnrollmentListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        qs = KidsEnrollment.objects.filter(kids_class_id=class_id).select_related("student")
        published_count = KidsAssignment.objects.filter(
            kids_class_id=class_id,
            is_published=True,
        ).count()
        submitted_rows = (
            KidsSubmission.objects.filter(
                assignment__kids_class_id=class_id,
                assignment__is_published=True,
            )
            .values("student_id")
            .annotate(n=Count("assignment", distinct=True))
        )
        submitted_by_student = {r["student_id"]: r["n"] for r in submitted_rows}
        return Response(
            KidsEnrollmentSerializer(
                qs,
                many=True,
                context={
                    "request": request,
                    "class_published_assignment_count": published_count,
                    "assignments_submitted_by_student": submitted_by_student,
                },
            ).data
        )


class KidsEnrollmentDestroyView(KidsAuthenticatedMixin, APIView):
    """Öğretmen: sınıftan öğrenci kaydını kaldırır (öğrenci hesabı silinmez)."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def delete(self, request, class_id, pk):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        enrollment = KidsEnrollment.objects.filter(pk=pk, kids_class_id=class_id).select_related(
            "student"
        ).first()
        if not enrollment:
            return Response(status=status.HTTP_404_NOT_FOUND)
        assignment_ids = KidsAssignment.objects.filter(kids_class_id=class_id).values_list(
            "id", flat=True
        )
        KidsSubmission.objects.filter(
            assignment_id__in=assignment_ids,
            student_id=enrollment.student_id,
        ).delete()
        enrollment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class KidsInviteCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def post(self, request):
        from .invite_email import kids_invite_signup_url, send_kids_parent_invite_email

        if not getattr(settings, "KIDS_INVITE_EMAIL_ENABLED", True):
            return Response(
                {"detail": "E-posta ile davet bu kurulumda devre dışı."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = KidsInviteCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cid = ser.validated_data["kids_class_id"]
        kids_class = KidsClass.objects.filter(pk=cid, teacher=request.user).first()
        if not kids_class:
            return Response(
                {"detail": "Sınıf bulunamadı veya yetkiniz yok."},
                status=status.HTTP_404_NOT_FOUND,
            )
        days = ser.validated_data["expires_days"]
        emails = ser.validated_data["emails"]
        teacher = request.user
        teacher_display = (teacher.first_name or "").strip() or teacher.email

        invites_out = []
        for email in emails:
            invite = KidsInvite.objects.create(
                kids_class=kids_class,
                parent_email=email,
                is_class_link=False,
                created_by=teacher,
                expires_at=timezone.now() + timedelta(days=days),
            )
            link = kids_invite_signup_url(invite.token)
            sent_ok, send_err = send_kids_parent_invite_email(
                to_email=email,
                signup_url=link,
                class_name=kids_class.name,
                teacher_display=teacher_display,
                expires_days=days,
            )
            row = KidsInviteSerializer(invite).data
            row["signup_url"] = link
            row["email_sent"] = sent_ok
            row["email_error"] = send_err
            invites_out.append(row)

        sent_n = sum(1 for r in invites_out if r["email_sent"])
        return Response(
            {
                "invites": invites_out,
                "summary": {
                    "total": len(invites_out),
                    "emails_sent": sent_n,
                    "emails_failed": len(invites_out) - sent_n,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class KidsAssignmentListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        enrolled = KidsEnrollment.objects.filter(kids_class_id=class_id).count()
        qs = (
            KidsAssignment.objects.filter(kids_class_id=class_id)
            .annotate(submission_count=Count("submissions"))
            .order_by("-created_at")
        )
        return Response(
            KidsAssignmentSerializer(
                qs,
                many=True,
                context={"request": request, "enrolled_student_count": enrolled},
            ).data
        )

    def post(self, request, class_id):
        kids_class = KidsClass.objects.filter(pk=class_id, teacher=request.user).first()
        if not kids_class:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsAssignmentSerializer(data={**request.data, "kids_class": kids_class.id})
        ser.is_valid(raise_exception=True)
        if ser.validated_data.get("require_video") and not getattr(
            settings, "KIDS_ASSIGNMENT_VIDEO_ENABLED", True
        ):
            return Response(
                {"detail": "Video ile proje oluşturma bu kurulumda kapalı."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        assignment = ser.save()
        if assignment.is_published:
            aid = assignment.pk
            transaction.on_commit(lambda: notify_students_new_assignment(aid))
        enrolled = KidsEnrollment.objects.filter(kids_class_id=class_id).count()
        a = (
            KidsAssignment.objects.filter(pk=assignment.pk)
            .annotate(submission_count=Count("submissions"))
            .first()
        )
        return Response(
            KidsAssignmentSerializer(
                a,
                context={"request": request, "enrolled_student_count": enrolled},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class KidsAssignmentDetailPatchView(KidsAuthenticatedMixin, APIView):
    """Öğretmen: proje güncelle. Yayındakilerde teslim başlangıcı ve proje (round) sayısı değişmez."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def patch(self, request, class_id, assignment_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        assignment = KidsAssignment.objects.filter(pk=assignment_id, kids_class_id=class_id).first()
        if not assignment:
            return Response(status=status.HTTP_404_NOT_FOUND)

        raw = request.data
        if hasattr(raw, "get") and raw.get("kids_class") is not None:
            try:
                if int(raw.get("kids_class")) != int(class_id):
                    return Response(
                        {"detail": "Sınıf değiştirilemez."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Geçersiz sınıf."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        planned = _assignment_editable_as_planned(assignment)
        enrolled = KidsEnrollment.objects.filter(kids_class_id=class_id).count()
        ser = KidsAssignmentSerializer(
            assignment,
            data=request.data,
            partial=True,
            context={
                "request": request,
                "enrolled_student_count": enrolled,
                "assignment_edit_planned": planned,
            },
        )
        ser.is_valid(raise_exception=True)
        if ser.validated_data.get("require_video") and not getattr(
            settings, "KIDS_ASSIGNMENT_VIDEO_ENABLED", True
        ):
            return Response(
                {"detail": "Video ile proje bu kurulumda kapalı."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = ser.save()
        aid = updated.pk
        transaction.on_commit(lambda a=aid: notify_students_new_assignment(a))
        a = (
            KidsAssignment.objects.filter(pk=updated.pk)
            .annotate(submission_count=Count("submissions"))
            .first()
        )
        return Response(
            KidsAssignmentSerializer(
                a,
                context={"request": request, "enrolled_student_count": enrolled},
            ).data,
        )


class KidsAssignmentSubmissionsDetailView(KidsAuthenticatedMixin, APIView):
    """Tek proje + o projeye ait teslimler (öğretmen)."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id, assignment_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        assignment = KidsAssignment.objects.filter(pk=assignment_id, kids_class_id=class_id).first()
        if not assignment:
            return Response(status=status.HTTP_404_NOT_FOUND)
        enrolled = KidsEnrollment.objects.filter(kids_class_id=class_id).count()
        a = (
            KidsAssignment.objects.filter(pk=assignment.pk)
            .annotate(submission_count=Count("submissions"))
            .first()
        )
        qs = (
            KidsSubmission.objects.filter(assignment=assignment)
            .select_related("student", "assignment")
            .order_by("student__first_name", "student__last_name", "student_id", "round_number", "-id")
        )
        pick_count = KidsSubmission.objects.filter(
            assignment=assignment, is_teacher_pick=True
        ).count()
        submitted_student_ids = set(
            KidsSubmission.objects.filter(assignment=assignment).values_list("student_id", flat=True)
        )
        not_submitted_students = []
        for en in (
            KidsEnrollment.objects.filter(kids_class_id=class_id)
            .select_related("student")
            .order_by("student__first_name", "student__last_name", "student__id")
        ):
            if en.student_id not in submitted_student_ids:
                not_submitted_students.append(
                    KidsUserSerializer(en.student, context={"request": request}).data
                )
        return Response(
            {
                "assignment": KidsAssignmentSerializer(
                    a,
                    context={"request": request, "enrolled_student_count": enrolled},
                ).data,
                "submissions": KidsTeacherSubmissionSerializer(
                    qs, many=True, context={"request": request}
                ).data,
                "not_submitted_students": not_submitted_students,
                "teacher_pick_limit": MAX_TEACHER_PICKS_PER_ASSIGNMENT,
                "teacher_pick_count": pick_count,
            }
        )


class KidsClassSubmissionListView(KidsAuthenticatedMixin, APIView):
    """Sınıftaki tüm proje teslimleri (yalnızca sınıf öğretmeni)."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        qs = (
            KidsSubmission.objects.filter(assignment__kids_class_id=class_id)
            .select_related("student", "assignment")
            .order_by(
                "assignment_id",
                "student__first_name",
                "student__last_name",
                "student_id",
                "round_number",
                "-id",
            )
        )
        ser = KidsTeacherSubmissionSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)


class KidsStudentDashboardView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        class_ids = KidsEnrollment.objects.filter(student=request.user).values_list(
            "kids_class_id", flat=True
        )
        now = timezone.now()
        assignments_qs = (
            KidsAssignment.objects.filter(
                kids_class_id__in=class_ids,
                is_published=True,
            )
            .filter(Q(submission_opens_at__isnull=True) | Q(submission_opens_at__lte=now))
            .select_related("kids_class")
            .order_by(F("submission_closes_at").asc(nulls_last=True), "id")
        )
        assignment_list = list(assignments_qs)
        aid_list = [a.id for a in assignment_list]
        sub_groups = {}
        if aid_list:
            subs = KidsSubmission.objects.filter(
                student=request.user, assignment_id__in=aid_list
            ).order_by("assignment_id", "round_number", "-id")
            for sub in subs:
                aid = sub.assignment_id
                sub_groups.setdefault(aid, []).append(sub)
            for aid in sub_groups:
                sub_groups[aid].sort(key=lambda s: s.round_number)
        class_qs = KidsClass.objects.filter(id__in=class_ids).select_related("school")
        return Response(
            {
                "classes": KidsClassSerializer(
                    class_qs,
                    many=True,
                    context={"request": request},
                ).data,
                "assignments": KidsAssignmentSerializer(
                    assignment_list,
                    many=True,
                    context={
                        "request": request,
                        "for_student": True,
                        "student_submissions_by_assignment": sub_groups,
                    },
                ).data,
            }
        )


class KidsStudentGameListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        grade = _student_grade_level(request.user)
        qs = KidsGame.objects.filter(
            is_active=True,
            min_grade__lte=grade,
            max_grade__gte=grade,
        ).order_by("sort_order", "title", "id")
        policy, _ = KidsParentGamePolicy.objects.get_or_create(student=request.user)
        progress_qs = KidsGameProgress.objects.filter(
            student=request.user, game_id__in=[g.id for g in qs]
        )
        progress_map = {p.game_id: p for p in progress_qs}
        today = timezone.localdate()
        progresses = []
        quests = []
        for game in qs:
            p = progress_map.get(game.id)
            if not p:
                p = KidsGameProgress(
                    student=request.user,
                    game=game,
                    current_difficulty=KidsGame.Difficulty.EASY,
                    streak_count=0,
                    best_score=0,
                )
            progresses.append(p)
            target = _daily_quest_score_target(p.current_difficulty)
            quests.append(
                {
                    "game_id": game.id,
                    "difficulty": p.current_difficulty,
                    "score_target": target,
                    "completed_today": p.daily_quest_completed_on == today,
                    "streak_count": int(p.streak_count or 0),
                }
            )
        payload = {
            "grade_level": grade,
            "policy": KidsParentGamePolicySerializer(policy).data,
            "today_minutes_played": _minutes_played_today(request.user),
            "games": KidsGameSerializer(qs, many=True).data,
            "progresses": KidsGameProgressSerializer(progresses, many=True).data,
            "daily_quests": quests,
        }
        return Response(payload)


class KidsStudentGameSessionStartView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, game_id: int):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        game = KidsGame.objects.filter(pk=game_id, is_active=True).first()
        if not game:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsGameSessionStartSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        grade = int(ser.validated_data.get("grade_level") or _student_grade_level(request.user))
        difficulty = ser.validated_data.get("difficulty") or KidsGame.Difficulty.EASY
        if grade < game.min_grade or grade > game.max_grade:
            return Response(
                {"detail": "Bu seviye bu oyun için uygun değil."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pol_err = _game_policy_error(request.user, game)
        if pol_err:
            return Response({"detail": pol_err}, status=status.HTTP_403_FORBIDDEN)
        active = KidsGameSession.objects.filter(
            student=request.user,
            status=KidsGameSession.SessionStatus.ACTIVE,
        ).first()
        if active:
            active.status = KidsGameSession.SessionStatus.ABORTED
            active.ended_at = timezone.now()
            active.duration_seconds = max(
                0, int((active.ended_at - active.started_at).total_seconds())
            )
            active.save(update_fields=["status", "ended_at", "duration_seconds", "updated_at"])
        session = KidsGameSession.objects.create(
            student=request.user,
            game=game,
            grade_level=grade,
            difficulty=difficulty,
        )
        prog, _ = KidsGameProgress.objects.get_or_create(
            student=request.user,
            game=game,
            defaults={"current_difficulty": difficulty},
        )
        if prog.current_difficulty != difficulty:
            prog.current_difficulty = difficulty
            prog.save(update_fields=["current_difficulty", "updated_at"])
        return Response(KidsGameSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class KidsStudentGameSessionCompleteView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id: int):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        session = KidsGameSession.objects.filter(
            pk=session_id,
            student=request.user,
        ).select_related("game").first()
        if not session:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if session.status != KidsGameSession.SessionStatus.ACTIVE:
            return Response(
                {"detail": "Bu oyun oturumu zaten kapatılmış."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = KidsGameSessionCompleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        now = timezone.now()
        session.ended_at = now
        session.duration_seconds = max(0, int((now - session.started_at).total_seconds()))
        session.score = int(ser.validated_data.get("score") or 0)
        session.progress_percent = int(ser.validated_data.get("progress_percent") or 0)
        session.status = ser.validated_data.get("status")
        session.save(
            update_fields=[
                "ended_at",
                "duration_seconds",
                "score",
                "progress_percent",
                "status",
                "updated_at",
            ]
        )
        _apply_game_rewards(request.user, session)
        progress, _ = KidsGameProgress.objects.get_or_create(
            student=request.user,
            game=session.game,
            defaults={"current_difficulty": session.difficulty},
        )
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        if progress.last_played_on == today:
            pass
        elif progress.last_played_on == yesterday:
            progress.streak_count = int(progress.streak_count or 0) + 1
        else:
            progress.streak_count = 1
        progress.last_played_on = today
        progress.best_score = max(int(progress.best_score or 0), int(session.score or 0))
        target = _daily_quest_score_target(progress.current_difficulty)
        if (
            session.status == KidsGameSession.SessionStatus.COMPLETED
            and int(session.progress_percent or 0) >= 70
            and int(session.score or 0) >= target
        ):
            progress.daily_quest_completed_on = today
        progress.save(
            update_fields=[
                "streak_count",
                "last_played_on",
                "best_score",
                "daily_quest_completed_on",
                "updated_at",
            ]
        )
        return Response(KidsGameSessionSerializer(session).data)


class KidsStudentGameSessionListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = (
            KidsGameSession.objects.filter(student=request.user)
            .select_related("game")
            .order_by("-created_at")[:40]
        )
        return Response({"sessions": KidsGameSessionSerializer(qs, many=True).data})


class KidsSubmissionCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = KidsSubmissionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        assignment = ser.validated_data["assignment"]
        if not KidsEnrollment.objects.filter(
            student=request.user,
            kids_class_id=assignment.kids_class_id,
        ).exists():
            return Response(
                {"detail": "Bu projeye teslim hakkınız yok."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not assignment.is_published:
            return Response(
                {"detail": "Bu proje yayından kaldırıldı."},
                status=status.HTTP_403_FORBIDDEN,
            )
        win_err = _assignment_submission_window_error(assignment)
        if win_err:
            return Response({"detail": win_err}, status=status.HTTP_400_BAD_REQUEST)
        kind = ser.validated_data.get("kind") or KidsSubmission.SubmissionKind.STEPS
        steps_payload = ser.validated_data.get("steps_payload")
        video_url = ser.validated_data.get("video_url") or ""
        err = _validate_kids_submission_for_assignment(
            assignment, kind, steps_payload, video_url
        )
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        round_number = int(ser.validated_data.get("round_number") or 1)
        existing = KidsSubmission.objects.filter(
            student=request.user,
            assignment=assignment,
            round_number=round_number,
        ).first()
        if existing and existing.teacher_reviewed_at:
            return Response(
                {"detail": "Bu teslim değerlendirildi; içerik artık değiştirilemez."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if existing:
            existing.kind = kind
            existing.steps_payload = steps_payload
            existing.video_url = video_url
            existing.caption = ser.validated_data.get("caption") or ""
            existing.save(
                update_fields=["kind", "steps_payload", "video_url", "caption", "updated_at"]
            )
            return Response(KidsSubmissionSerializer(existing).data, status=status.HTTP_200_OK)
        sub = KidsSubmission.objects.create(
            assignment=assignment,
            student=request.user,
            round_number=round_number,
            kind=kind,
            steps_payload=steps_payload,
            video_url=video_url,
            caption=ser.validated_data.get("caption") or "",
        )
        sid = sub.pk
        transaction.on_commit(lambda: notify_teacher_submission_received(sid))
        try_award_first_submit_badge(request.user.id)
        sync_growth_milestone_badges(request.user.id)
        return Response(
            KidsSubmissionSerializer(sub).data,
            status=status.HTTP_201_CREATED,
        )


class KidsStudentSubmissionForAssignmentView(KidsAuthenticatedMixin, APIView):
    """Öğrenci: bir proje için kendi son teslimini getirir (düzenleme öncesi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        raw_id = request.query_params.get("assignment_id")
        if not raw_id or not str(raw_id).isdigit():
            return Response(
                {"detail": "assignment_id sorgu parametresi gerekli."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        assignment_id = int(raw_id)
        assignment = KidsAssignment.objects.filter(pk=assignment_id).first()
        if not assignment:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not KidsEnrollment.objects.filter(
            student=request.user,
            kids_class_id=assignment.kids_class_id,
        ).exists():
            return Response(
                {"detail": "Bu projeye erişiminiz yok."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not _assignment_visible_to_students(assignment):
            return Response(
                {"detail": "Bu proje henüz öğrencilere açılmadı (teslim başlangıcı gelince listede görünür)."},
                status=status.HTTP_403_FORBIDDEN,
            )
        total = int(assignment.submission_rounds or 1)
        rounds_out = []
        for r in range(1, total + 1):
            sub = KidsSubmission.objects.filter(
                student=request.user,
                assignment=assignment,
                round_number=r,
            ).first()
            rounds_out.append(
                {
                    "round_number": r,
                    "submission": KidsSubmissionSerializer(sub).data if sub else None,
                }
            )
        return Response(
            {
                "submission_rounds": total,
                "rounds": rounds_out,
            }
        )


class KidsSubmissionReviewView(KidsAuthenticatedMixin, APIView):
    """Öğretmen: teslimi değerlendirir (son teslimden sonra); ilk kayıtta büyüme puanı eklenir."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def patch(self, request, class_id, submission_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        sub = (
            KidsSubmission.objects.filter(
                pk=submission_id,
                assignment__kids_class_id=class_id,
            )
            .select_related("assignment", "student")
            .first()
        )
        if not sub:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not _assignment_teacher_review_allowed(sub.assignment):
            return Response(
                {
                    "detail": "Değerlendirme, son teslim tarihinden sonra yapılabilir.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = KidsSubmissionReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        valid = ser.validated_data["teacher_review_valid"]
        positive = ser.validated_data.get("teacher_review_positive")
        note = ser.validated_data.get("teacher_note_to_student") or ""
        was_reviewed = sub.teacher_reviewed_at is not None
        with transaction.atomic():
            locked = (
                KidsSubmission.objects.select_for_update()
                .filter(pk=sub.pk)
                .select_related("student")
                .first()
            )
            if not locked:
                return Response(status=status.HTTP_404_NOT_FOUND)
            locked.teacher_review_valid = valid
            locked.teacher_review_positive = positive
            locked.teacher_note_to_student = note
            locked.teacher_reviewed_at = timezone.now()
            locked.save(
                update_fields=[
                    "teacher_review_valid",
                    "teacher_review_positive",
                    "teacher_note_to_student",
                    "teacher_reviewed_at",
                    "updated_at",
                ]
            )
            if not was_reviewed:
                delta = _growth_points_for_first_review(valid, positive)
                if delta and locked.student.role == KidsUserRole.STUDENT:
                    KidsUser.objects.filter(pk=locked.student_id).update(
                        growth_points=F("growth_points") + delta
                    )
        locked.refresh_from_db()
        if locked.student.role == KidsUserRole.STUDENT:
            sync_growth_milestone_badges(locked.student_id)
        return Response(
            KidsTeacherSubmissionSerializer(
                locked, context={"request": request}
            ).data,
        )


class KidsSubmissionHighlightView(KidsAuthenticatedMixin, APIView):
    """Öğretmen: teslimi proje yıldızı olarak işaretle (sınırlı sayıda)."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def patch(self, request, class_id, submission_id):
        if not KidsClass.objects.filter(pk=class_id, teacher=request.user).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)
        sub = (
            KidsSubmission.objects.filter(
                pk=submission_id,
                assignment__kids_class_id=class_id,
            )
            .select_related("assignment", "student")
            .first()
        )
        if not sub:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ser = KidsSubmissionHighlightSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        want = ser.validated_data["is_teacher_pick"]
        try:
            locked, _ = apply_teacher_pick(sub, want)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            KidsTeacherSubmissionSerializer(
                locked, context={"request": request}
            ).data,
        )


class KidsStudentRoadmapView(KidsAuthenticatedMixin, APIView):
    """Öğrenci: rozet yolu (Duolingo tarzı düğümler + proje yıldızları)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        request.user.refresh_from_db()
        return Response(build_student_roadmap(request.user))


class KidsFreestyleListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = KidsFreestylePost.objects.filter(is_visible=True).select_related("student")[:50]
        data = []
        for p in qs:
            data.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "description": p.description,
                    "media_urls": p.media_urls,
                    "created_at": p.created_at,
                    "student_name": p.student.full_name or p.student.email,
                }
            )
        return Response(data)

    def post(self, request):
        if not is_kids_student_user(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ser = KidsFreestylePostSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        post = KidsFreestylePost.objects.create(
            student=request.user,
            title=ser.validated_data["title"],
            description=ser.validated_data.get("description") or "",
            media_urls=ser.validated_data.get("media_urls") or [],
        )
        return Response(KidsFreestylePostSerializer(post).data, status=status.HTTP_201_CREATED)


class KidsNotificationListView(KidsAuthenticatedMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = KidsNotificationSerializer

    def get_queryset(self):
        u = self.request.user
        if is_kids_student_user(u):
            q = Q(recipient_student=u)
        elif is_main_user(u):
            q = Q(recipient_user=u)
        else:
            q = Q(pk__in=[])
        return (
            KidsNotification.objects.filter(q)
            .select_related(
                "assignment",
                "submission",
                "challenge",
                "challenge_invite",
                "sender_student",
                "sender_user",
            )
            .order_by("-created_at")
        )


class KidsNotificationMarkReadView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        u = request.user
        if is_kids_student_user(u):
            n = KidsNotification.objects.filter(pk=pk, recipient_student=u).first()
        elif is_main_user(u):
            n = KidsNotification.objects.filter(pk=pk, recipient_user=u).first()
        else:
            n = None
        if not n:
            return Response(status=status.HTTP_404_NOT_FOUND)
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response(KidsNotificationSerializer(n).data)


class KidsNotificationUnreadCountView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        if is_kids_student_user(u):
            q = Q(recipient_student=u)
        elif is_main_user(u):
            q = Q(recipient_user=u)
        else:
            q = Q(pk__in=[])
        c = KidsNotification.objects.filter(q, is_read=False).count()
        return Response({"unread_count": c})


class KidsNotificationMarkAllReadView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        u = request.user
        if is_kids_student_user(u):
            q = Q(recipient_student=u)
        elif is_main_user(u):
            q = Q(recipient_user=u)
        else:
            q = Q(pk__in=[])
        KidsNotification.objects.filter(q, is_read=False).update(is_read=True)
        return Response({"message": "Tamam"})


class KidsFCMRegisterView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            return Response({"error": "token gerekli"}, status=status.HTTP_400_BAD_REQUEST)
        device_name = (request.data.get("device_name") or "")[:100]
        u = request.user
        defaults = {"device_name": device_name}
        if is_kids_student_user(u):
            defaults["kids_user"] = u
            defaults["user"] = None
        elif is_main_user(u):
            defaults["user"] = u
            defaults["kids_user"] = None
        else:
            return Response({"error": "desteklenmeyen kullanıcı"}, status=status.HTTP_400_BAD_REQUEST)
        KidsFCMDeviceToken.objects.update_or_create(token=token, defaults=defaults)
        return Response({"message": "Token kaydedildi"})


def _meb_match_province_q(province: str) -> Q:
    """`province` alanı, `line_full` ön eki veya tablodaki `il_plaka` (il adı seçimine göre)."""
    p = (province or "").strip()
    q = Q(province=p) | Q(province="", line_full__startswith=f"{p} - ")
    pk = il_name_to_plaka_int(p)
    if pk:
        plaka_q = Q()
        for variant in il_plaka_db_variants(pk):
            plaka_q |= Q(il_plaka=variant)
        q |= Q(province="") & plaka_q
    return q


class MebProvinceListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request):
        names = set(
            MebSchoolDirectory.objects.exclude(province="")
            .values_list("province", flat=True)
            .distinct()
        )
        for lf in (
            MebSchoolDirectory.objects.filter(province="")
            .exclude(line_full="")
            .values_list("line_full", flat=True)
            .distinct()
            .iterator(chunk_size=2000)
        ):
            il, _ = split_line_full_location(lf)
            if il:
                names.add(il)
        for raw in (
            MebSchoolDirectory.objects.filter(province="")
            .exclude(il_plaka="")
            .values_list("il_plaka", flat=True)
            .distinct()
        ):
            pn = province_name_from_il_plaka_raw(raw)
            if pn:
                names.add(pn)
        ordered = sorted(names, key=lambda x: (x.replace("İ", "I").upper(), x))
        return Response({"provinces": ordered})


class MebDistrictListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request):
        province = (request.query_params.get("province") or "").strip()
        if not province:
            return Response(
                {"detail": "province parametresi gerekli."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        base = MebSchoolDirectory.objects.filter(_meb_match_province_q(province))
        dnames = set()
        for d in base.exclude(district="").values_list("district", flat=True).distinct():
            if d:
                dnames.add(d)
        for lf in (
            base.filter(district="")
            .exclude(line_full="")
            .values_list("line_full", flat=True)
            .distinct()
            .iterator(chunk_size=2000)
        ):
            _, ilce = split_line_full_location(lf)
            if ilce:
                dnames.add(ilce)
        ordered = sorted(dnames, key=lambda x: (x.replace("İ", "I").upper(), x))
        return Response({"districts": ordered})


class MebSchoolPickListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request):
        province = (request.query_params.get("province") or "").strip()
        district = (request.query_params.get("district") or "").strip()
        if not province or not district:
            return Response(
                {"detail": "province ve district parametreleri gerekli."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        q = (request.query_params.get("q") or "").strip()
        try:
            limit = int(request.query_params.get("limit") or 80)
        except ValueError:
            limit = 80
        limit = max(5, min(limit, 200))
        p, d = province.strip(), district.strip()
        prefix = f"{p} - {d} - "
        qs = MebSchoolDirectory.objects.filter(
            Q(province=p, district=d)
            | Q(line_full__startswith=prefix)
            | (_meb_match_province_q(p) & Q(district=d))
        )
        if q:
            qs = qs.filter(name__icontains=q)
        rows = qs.order_by("name")[:limit]
        return Response(
            {
                "schools": [
                    {
                        "yol": r.yol,
                        "name": r.name,
                        "province": r.province,
                        "district": r.district,
                        "line_full": r.line_full,
                    }
                    for r in rows
                ]
            }
        )


class MebSchoolManualCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsAdmin]

    def post(self, request):
        province = (request.data.get("province") or "").strip()
        district = (request.data.get("district") or "").strip()
        name = (request.data.get("name") or "").strip()
        if not province or not district or not name:
            return Response(
                {"detail": "province, district ve name zorunludur."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        province = province[:100]
        district = district[:100]
        name = name[:500]
        line_full = f"{province} - {district} - {name}"
        existing = MebSchoolDirectory.objects.filter(
            province__iexact=province,
            district__iexact=district,
            name__iexact=name,
        ).first()
        created = False
        if existing:
            row = existing
        else:
            pk = il_name_to_plaka_int(province)
            row = MebSchoolDirectory.objects.create(
                yol=f"manual-{uuid.uuid4().hex[:24]}",
                province=province,
                district=district,
                name=name,
                line_full=line_full,
                il_plaka=str(pk) if pk else "",
            )
            created = True

        return Response(
            {
                "created": created,
                "school": {
                    "yol": row.yol,
                    "name": row.name,
                    "province": row.province,
                    "district": row.district,
                    "line_full": row.line_full,
                },
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class KidsWeeklyChampionView(KidsAuthenticatedMixin, APIView):
    """Haftanın mucidi: seçilen sınıfta bu hafta en çok teslim sayısı."""

    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id):
        kids_class = KidsClass.objects.filter(pk=class_id, teacher=request.user).first()
        if not kids_class:
            return Response(status=status.HTTP_404_NOT_FOUND)
        start = timezone.now() - timedelta(days=7)
        student_ids = KidsEnrollment.objects.filter(kids_class=kids_class).values_list(
            "student_id", flat=True
        )
        rows = (
            KidsSubmission.objects.filter(
                student_id__in=student_ids,
                created_at__gte=start,
            )
            .values("student_id")
            .annotate(c=Count("id"))
            .order_by("-c")[:5]
        )
        out = []
        for row in rows:
            try:
                u = KidsUser.objects.get(pk=row["student_id"])
                out.append(
                    {
                        "student": _kids_user_payload(u, request),
                        "submission_count": row["c"],
                    }
                )
            except KidsUser.DoesNotExist:
                continue
        return Response({"week_start": start.isoformat(), "top": out})
