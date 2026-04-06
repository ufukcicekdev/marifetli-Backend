"""Sınıf challenge API: öğrenci önerisi, öğretmen onayı, davet, öğretmen yarışması."""
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework import status

from .challenge_logic import (
    build_invite_notification_message,
    can_accept_peer_invite,
    can_propose_free_parent_challenge,
    can_propose_student_challenge,
    clear_student_peer_active_memberships_except,
    ensure_challenge_time_state,
    peer_student_challenge_actions_allowed,
    student_enrolled_in_class,
)
from .models import (
    KidsChallenge,
    KidsChallengeInvite,
    KidsChallengeMember,
    KidsClass,
    KidsEnrollment,
    KidsNotification,
    KidsUser,
    KidsUserRole,
)
from .badges import on_challenge_member_created
from .auth_utils import is_kids_student_user
from .notifications_service import create_kids_notification
from core.i18n_catalog import translate
from core.i18n_resolve import language_for_kids_student, language_from_user
from .permissions import IsKidsParent, IsKidsTeacherOrAdmin
from .serializers import (
    KidsChallengeInviteCreateSerializer,
    KidsChallengeInviteReadSerializer,
    KidsChallengeInviteRespondSerializer,
    KidsChallengeReadSerializer,
    KidsParentFreeChallengeReviewSerializer,
    KidsStudentChallengeProposeSerializer,
    KidsTeacherChallengeCreateSerializer,
    KidsTeacherChallengeReviewSerializer,
)
from .views import KidsAuthenticatedMixin, _teacher_class_queryset

logger = logging.getLogger(__name__)

# Tekil davet sonuçları (toplu davet sayımı için).
_PEER_INV_ERR_SELF = "self"
_PEER_INV_ERR_NOT_ENROLLED = "not_enrolled"
_PEER_INV_ERR_ALREADY_MEMBER = "already_member"
_PEER_INV_ERR_PENDING_DUP = "pending_duplicate"


def _create_peer_invite(
    ch: KidsChallenge,
    inviter: KidsUser,
    invitee: KidsUser,
    personal: str,
) -> tuple[KidsChallengeInvite | None, str | None]:
    """
    Davet kaydı + bildirim. Başarıda (invite, None); atlanırsa (None, reason).
    reason: self | not_enrolled | already_member | pending_duplicate
    """
    if invitee.pk == inviter.pk:
        return None, _PEER_INV_ERR_SELF
    if not ch.kids_class_id or ch.peer_scope == KidsChallenge.PeerScope.FREE_PARENT:
        return None, _PEER_INV_ERR_NOT_ENROLLED
    if not student_enrolled_in_class(invitee.pk, ch.kids_class_id):
        return None, _PEER_INV_ERR_NOT_ENROLLED
    if KidsChallengeMember.objects.filter(challenge=ch, student_id=invitee.pk).exists():
        return None, _PEER_INV_ERR_ALREADY_MEMBER
    personal_t = (personal or "").strip()[:500]
    with transaction.atomic():
        inv, created = KidsChallengeInvite.objects.get_or_create(
            challenge=ch,
            invitee=invitee,
            defaults={
                "inviter": inviter,
                "personal_message": personal_t,
                "status": KidsChallengeInvite.InviteStatus.PENDING,
            },
        )
        if not created:
            if inv.status == KidsChallengeInvite.InviteStatus.PENDING:
                return None, _PEER_INV_ERR_PENDING_DUP
            inv.inviter = inviter
            inv.personal_message = personal_t
            inv.status = KidsChallengeInvite.InviteStatus.PENDING
            inv.responded_at = None
            inv.save(
                update_fields=["inviter", "personal_message", "status", "responded_at"]
            )
    msg = build_invite_notification_message(
        inviter,
        ch,
        personal_message=personal_t,
        lang=language_for_kids_student(invitee),
    )
    try:
        create_kids_notification(
            notification_type=KidsNotification.NotificationType.CHALLENGE_INVITE,
            message=msg,
            recipient_student=invitee,
            sender_student=inviter,
            challenge=ch,
            challenge_invite=inv,
        )
    except Exception:
        logger.exception("challenge invite notify")
    inv = KidsChallengeInvite.objects.select_related("challenge", "challenge__kids_class", "inviter").prefetch_related(
        "challenge__members__student"
    ).get(pk=inv.pk)
    return inv, None


def _student_challenge_access_q(user_id: int):
    return (
        Q(created_by_student_id=user_id)
        | Q(members__student_id=user_id)
        | Q(invites__invitee_id=user_id)
    )


class KidsStudentChallengeListCreateView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        uid = request.user.pk
        outgoing_inv_prefetch = Prefetch(
            "invites",
            queryset=KidsChallengeInvite.objects.filter(
                inviter_id=uid,
                status=KidsChallengeInvite.InviteStatus.PENDING,
            ).select_related("invitee"),
        )
        qs = (
            KidsChallenge.objects.filter(_student_challenge_access_q(uid))
            .distinct()
            .select_related("kids_class")
            .prefetch_related("members__student", outgoing_inv_prefetch)
            .order_by("-created_at")
        )
        challenges = list(qs)
        for c in challenges:
            ensure_challenge_time_state(c)
        ser = KidsChallengeReadSerializer(challenges, many=True, context={"request": request})
        invites = list(
            KidsChallengeInvite.objects.filter(
                invitee_id=uid, status=KidsChallengeInvite.InviteStatus.PENDING
            )
            .select_related("challenge", "challenge__kids_class", "inviter")
            .prefetch_related("challenge__members__student")
        )
        for inv in invites:
            ensure_challenge_time_state(inv.challenge)
        inv_ser = KidsChallengeInviteReadSerializer(invites, many=True, context={"request": request})
        return Response(
            {
                "challenges": ser.data,
                "pending_invites": inv_ser.data,
                "allow_free_parent_challenge": bool(
                    getattr(settings, "KIDS_STUDENT_FREE_CHALLENGE_ENABLED", True)
                ),
            }
        )

    def post(self, request):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = KidsStudentChallengeProposeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        scope = ser.validated_data.get("peer_scope") or KidsChallenge.PeerScope.CLASS_PEER
        free_enabled = bool(
            getattr(settings, "KIDS_STUDENT_FREE_CHALLENGE_ENABLED", True)
        )
        if scope == KidsChallenge.PeerScope.FREE_PARENT and not free_enabled:
            return Response(
                {"detail": "Serbest yarışma şu anda kapalı."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if scope == KidsChallenge.PeerScope.FREE_PARENT:
            ok, err = can_propose_free_parent_challenge(request.user)
            if not ok:
                return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
            parent = request.user.parent_account
            if not parent:
                return Response(
                    {"detail": "Veli hesabı bulunamadı; serbest yarışma önerilemez."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                ch = KidsChallenge.objects.create(
                    kids_class=None,
                    peer_scope=KidsChallenge.PeerScope.FREE_PARENT,
                    source=KidsChallenge.Source.STUDENT,
                    created_by_student=request.user,
                    title=ser.validated_data["title"].strip(),
                    description=(ser.validated_data.get("description") or "").strip(),
                    rules_or_goal=(ser.validated_data.get("rules_or_goal") or "").strip(),
                    submission_rounds=int(ser.validated_data.get("submission_rounds") or 1),
                    status=KidsChallenge.Status.PENDING_PARENT,
                    starts_at=ser.validated_data["starts_at"],
                    ends_at=ser.validated_data["ends_at"],
                )
            who = request.user.full_name or request.user.email
            _lang = language_from_user(parent)
            msg = translate(
                _lang,
                "kids.notif.challenge_pending_parent",
                who=who,
                title=ch.title,
            )
            try:
                create_kids_notification(
                    notification_type=KidsNotification.NotificationType.CHALLENGE_PENDING_PARENT,
                    message=msg,
                    recipient_user=parent,
                    sender_student=request.user,
                    challenge=ch,
                )
            except Exception:
                logger.exception("challenge pending parent notify")
            ch = KidsChallenge.objects.select_related("kids_class").prefetch_related("members__student").get(pk=ch.pk)
            return Response(
                KidsChallengeReadSerializer(ch, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        cid = ser.validated_data["kids_class_id"]
        try:
            kc = KidsClass.objects.get(pk=cid)
        except KidsClass.DoesNotExist:
            return Response({"detail": "Sınıf bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        ok, err = can_propose_student_challenge(request.user, kc)
        if not ok:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            ch = KidsChallenge.objects.create(
                kids_class=kc,
                peer_scope=KidsChallenge.PeerScope.CLASS_PEER,
                source=KidsChallenge.Source.STUDENT,
                created_by_student=request.user,
                title=ser.validated_data["title"].strip(),
                description=(ser.validated_data.get("description") or "").strip(),
                rules_or_goal=(ser.validated_data.get("rules_or_goal") or "").strip(),
                submission_rounds=int(ser.validated_data.get("submission_rounds") or 1),
                status=KidsChallenge.Status.PENDING_TEACHER,
                starts_at=ser.validated_data["starts_at"],
                ends_at=ser.validated_data["ends_at"],
            )
        teacher = kc.teacher
        who = request.user.full_name or request.user.email
        _lang = language_from_user(teacher)
        msg = translate(_lang, "kids.notif.challenge_pending_teacher", who=who, title=ch.title)
        try:
            create_kids_notification(
                notification_type=KidsNotification.NotificationType.CHALLENGE_PENDING_TEACHER,
                message=msg,
                recipient_user=teacher,
                sender_student=request.user,
                challenge=ch,
            )
        except Exception:
            logger.exception("challenge pending teacher notify")
        ch = KidsChallenge.objects.select_related("kids_class").prefetch_related("members__student").get(pk=ch.pk)
        return Response(
            KidsChallengeReadSerializer(ch, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class KidsStudentChallengeDetailView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        uid = request.user.pk
        outgoing_inv_prefetch = Prefetch(
            "invites",
            queryset=KidsChallengeInvite.objects.filter(
                inviter_id=uid,
                status=KidsChallengeInvite.InviteStatus.PENDING,
            ).select_related("invitee"),
        )
        try:
            ch = (
                KidsChallenge.objects.filter(pk=pk)
                .filter(_student_challenge_access_q(uid))
                .distinct()
                .select_related("kids_class")
                .prefetch_related("members__student", outgoing_inv_prefetch)
                .get()
            )
        except KidsChallenge.DoesNotExist:
            return Response({"detail": "Bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        ensure_challenge_time_state(ch)
        ch.refresh_from_db()
        return Response(KidsChallengeReadSerializer(ch, context={"request": request}).data)


class KidsStudentClassmatesView(KidsAuthenticatedMixin, APIView):
    """Aynı sınıftaki diğer öğrenciler (davet hedefi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, class_id):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not student_enrolled_in_class(request.user.pk, class_id):
            return Response({"detail": "Bu sınıfta kayıtlı değilsin."}, status=status.HTTP_403_FORBIDDEN)
        ids = KidsEnrollment.objects.filter(kids_class_id=class_id).exclude(student=request.user).values_list(
            "student_id", flat=True
        )
        students = KidsUser.objects.filter(pk__in=ids, role=KidsUserRole.STUDENT).order_by(
            "first_name", "last_name", "email"
        )
        from .serializers import KidsUserSerializer

        return Response({"classmates": KidsUserSerializer(students, many=True, context={"request": request}).data})


class KidsStudentChallengeInviteView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            ch = KidsChallenge.objects.select_related("kids_class").get(pk=pk)
        except KidsChallenge.DoesNotExist:
            return Response({"detail": "Yarışma bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        if ch.peer_scope == KidsChallenge.PeerScope.FREE_PARENT:
            return Response(
                {"detail": "Serbest yarışmalarda sınıf arkadaşı daveti yok; veli onayıyla yalnızca sen katılırsın."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ensure_challenge_time_state(ch)
        ch.refresh_from_db()
        if ch.status != KidsChallenge.Status.ACTIVE:
            return Response(
                {"detail": "Yalnızca onaylanmış ve devam eden yarışmalara davet gönderebilirsin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ok_t, err_t = peer_student_challenge_actions_allowed(ch)
        if not ok_t:
            return Response({"detail": err_t}, status=status.HTTP_400_BAD_REQUEST)
        if not KidsChallengeMember.objects.filter(challenge=ch, student=request.user).exists():
            return Response(
                {"detail": "Bu yarışmaya davet göndermek için önce üye olmalısın."},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = KidsChallengeInviteCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        personal = (ser.validated_data.get("personal_message") or "").strip()

        if ser.validated_data.get("invite_all_classmates"):
            enrolled_ids = list(
                KidsEnrollment.objects.filter(kids_class_id=ch.kids_class_id)
                .exclude(student_id=request.user.pk)
                .values_list("student_id", flat=True)
            )
            invited_count = 0
            skipped_already_in_challenge = 0
            skipped_pending_invite = 0
            skipped_other = 0
            for sid in enrolled_ids:
                invitee = KidsUser.objects.filter(pk=sid, role=KidsUserRole.STUDENT).first()
                if not invitee:
                    continue
                _inv, err = _create_peer_invite(ch, request.user, invitee, personal)
                if err is None:
                    invited_count += 1
                elif err == _PEER_INV_ERR_ALREADY_MEMBER:
                    skipped_already_in_challenge += 1
                elif err == _PEER_INV_ERR_PENDING_DUP:
                    skipped_pending_invite += 1
                else:
                    skipped_other += 1
            if invited_count == 0:
                return Response(
                    {
                        "detail": "Yeni davet gönderilemedi: sınıf arkadaşların ya zaten yarışmada ya da bekleyen daveti var.",
                        "bulk": True,
                        "invited_count": 0,
                        "skipped_already_in_challenge": skipped_already_in_challenge,
                        "skipped_pending_invite": skipped_pending_invite,
                        "skipped_other": skipped_other,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {
                    "bulk": True,
                    "invited_count": invited_count,
                    "skipped_already_in_challenge": skipped_already_in_challenge,
                    "skipped_pending_invite": skipped_pending_invite,
                    "skipped_other": skipped_other,
                },
                status=status.HTTP_201_CREATED,
            )

        invitee_id = ser.validated_data["invitee_user_id"]
        if invitee_id == request.user.pk:
            return Response({"detail": "Kendine davet gönderemezsin."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            invitee = KidsUser.objects.get(pk=invitee_id, role=KidsUserRole.STUDENT)
        except KidsUser.DoesNotExist:
            return Response({"detail": "Öğrenci bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        inv, err = _create_peer_invite(ch, request.user, invitee, personal)
        if err == _PEER_INV_ERR_PENDING_DUP:
            return Response({"detail": "Bu arkadaşa zaten bekleyen bir davet var."}, status=status.HTTP_400_BAD_REQUEST)
        if err == _PEER_INV_ERR_ALREADY_MEMBER:
            return Response({"detail": "Bu arkadaş zaten yarışmada."}, status=status.HTTP_400_BAD_REQUEST)
        if err == _PEER_INV_ERR_NOT_ENROLLED:
            return Response(
                {"detail": "Davet yalnızca aynı sınıftaki arkadaşlarına gönderilebilir."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if err == _PEER_INV_ERR_SELF:
            return Response({"detail": "Kendine davet gönderemezsin."}, status=status.HTTP_400_BAD_REQUEST)
        assert inv is not None
        return Response(
            KidsChallengeInviteReadSerializer(inv, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class KidsStudentChallengeInviteRespondView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            inv = KidsChallengeInvite.objects.select_related("challenge", "challenge__kids_class").get(
                pk=pk, invitee=request.user
            )
        except KidsChallengeInvite.DoesNotExist:
            return Response({"detail": "Davet bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        if inv.status != KidsChallengeInvite.InviteStatus.PENDING:
            return Response({"detail": "Bu davet artık geçerli değil."}, status=status.HTTP_400_BAD_REQUEST)
        ser = KidsChallengeInviteRespondSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ser.validated_data["action"]
        ch = inv.challenge
        ensure_challenge_time_state(ch)
        ch.refresh_from_db()
        now = timezone.now()
        if action == "decline":
            inv.status = KidsChallengeInvite.InviteStatus.DECLINED
            inv.responded_at = now
            inv.save(update_fields=["status", "responded_at"])
            return Response({"status": "declined"})
        if ch.status != KidsChallenge.Status.ACTIVE:
            return Response({"detail": "Bu yarışma artık aktif değil."}, status=status.HTTP_400_BAD_REQUEST)
        ok_t, err_t = peer_student_challenge_actions_allowed(ch)
        if not ok_t:
            return Response({"detail": err_t}, status=status.HTTP_400_BAD_REQUEST)
        ok, err = can_accept_peer_invite(request.user, ch)
        if not ok:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            inv.status = KidsChallengeInvite.InviteStatus.ACCEPTED
            inv.responded_at = now
            inv.save(update_fields=["status", "responded_at"])
            _, chm_created = KidsChallengeMember.objects.get_or_create(
                challenge=ch,
                student=request.user,
                defaults={"is_initiator": False},
            )
            on_challenge_member_created(request.user.id, chm_created)
        ch = KidsChallenge.objects.select_related("kids_class").prefetch_related("members__student").get(pk=ch.pk)
        return Response(KidsChallengeReadSerializer(ch, context={"request": request}).data)


class KidsStudentChallengeInviteRevokeView(KidsAuthenticatedMixin, APIView):
    """Daveti gönderen öğrenci, karşı taraf kabul etmeden daveti geri çeker."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_kids_student_user(request.user):
            return Response(
                {"detail": "Bu uç nokta yalnızca öğrenci hesapları içindir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            inv = KidsChallengeInvite.objects.select_related("challenge").get(pk=pk, inviter=request.user)
        except KidsChallengeInvite.DoesNotExist:
            return Response({"detail": "Davet bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        if inv.status != KidsChallengeInvite.InviteStatus.PENDING:
            return Response(
                {"detail": "Bu davet artık bekleyen durumda değil."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        inv.status = KidsChallengeInvite.InviteStatus.REVOKED
        inv.responded_at = now
        inv.save(update_fields=["status", "responded_at"])
        return Response({"status": "revoked"})


class KidsTeacherChallengeListView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def get(self, request, class_id):
        kc = _teacher_class_queryset(request.user).filter(pk=class_id).first()
        if not kc:
            return Response({"detail": "Sınıf bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        st = (request.query_params.get("status") or "").strip()
        qs = KidsChallenge.objects.filter(kids_class=kc).select_related("kids_class").prefetch_related("members__student")
        allowed_status = {c[0] for c in KidsChallenge.Status.choices}
        if st in allowed_status:
            qs = qs.filter(status=st)
        qs = qs.order_by("-created_at")
        ch_list = list(qs)
        for c in ch_list:
            ensure_challenge_time_state(c)
        return Response({"challenges": KidsChallengeReadSerializer(ch_list, many=True, context={"request": request}).data})

    def post(self, request, class_id):
        """Öğretmen doğrudan aktif yarışma oluşturur; seçilen öğrenciler üye olur (öğrenci kaynaklı çakışmalar temizlenir)."""
        kc = _teacher_class_queryset(request.user).filter(pk=class_id).first()
        if not kc:
            return Response({"detail": "Sınıf bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        ser = KidsTeacherChallengeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        student_ids = list(dict.fromkeys(ser.validated_data.get("student_ids") or []))
        now = timezone.now()
        with transaction.atomic():
            ch = KidsChallenge.objects.create(
                kids_class=kc,
                peer_scope=KidsChallenge.PeerScope.CLASS_PEER,
                source=KidsChallenge.Source.TEACHER,
                created_by_teacher=request.user,
                title=ser.validated_data["title"].strip(),
                description=(ser.validated_data.get("description") or "").strip(),
                rules_or_goal=(ser.validated_data.get("rules_or_goal") or "").strip(),
                submission_rounds=int(ser.validated_data.get("submission_rounds") or 1),
                status=KidsChallenge.Status.ACTIVE,
                reviewed_at=now,
                reviewed_by=request.user,
                activated_at=now,
            )
            for sid in student_ids:
                if not KidsEnrollment.objects.filter(kids_class=kc, student_id=sid).exists():
                    continue
                stu = KidsUser.objects.filter(pk=sid, role=KidsUserRole.STUDENT).first()
                if not stu:
                    continue
                clear_student_peer_active_memberships_except(stu.pk, kc.pk, ch.pk)
                _, chm_created = KidsChallengeMember.objects.get_or_create(
                    challenge=ch,
                    student=stu,
                    defaults={"is_initiator": False},
                )
                on_challenge_member_created(stu.pk, chm_created)
        ch = KidsChallenge.objects.select_related("kids_class").prefetch_related("members__student").get(pk=ch.pk)
        return Response(
            KidsChallengeReadSerializer(ch, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class KidsTeacherChallengeReviewView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsTeacherOrAdmin]

    def post(self, request, class_id, pk):
        kc = _teacher_class_queryset(request.user).filter(pk=class_id).first()
        if not kc:
            return Response({"detail": "Sınıf bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        try:
            ch = KidsChallenge.objects.select_related("kids_class", "created_by_student").get(pk=pk, kids_class=kc)
        except KidsChallenge.DoesNotExist:
            return Response({"detail": "Yarışma bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        if ch.status != KidsChallenge.Status.PENDING_TEACHER or ch.source != KidsChallenge.Source.STUDENT:
            return Response({"detail": "Bu kayıt öğretmen onayı beklemiyor."}, status=status.HTTP_400_BAD_REQUEST)
        ser = KidsTeacherChallengeReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        decision = ser.validated_data["decision"]
        now = timezone.now()
        if decision == "reject":
            note = (ser.validated_data.get("rejection_note") or "").strip()[:600]
            with transaction.atomic():
                ch.status = KidsChallenge.Status.REJECTED
                ch.teacher_rejection_note = note
                ch.reviewed_at = now
                ch.reviewed_by = request.user
                ch.save(update_fields=["status", "teacher_rejection_note", "reviewed_at", "reviewed_by", "updated_at"])
            if ch.created_by_student:
                _lang = language_for_kids_student(ch.created_by_student)
                base = translate(_lang, "kids.notif.challenge_rejected_teacher", title=ch.title)
                msg = (
                    translate(_lang, "kids.notif.challenge_rejected_teacher_note", base=base, note=note)
                    if note
                    else base
                )
                try:
                    create_kids_notification(
                        notification_type=KidsNotification.NotificationType.CHALLENGE_REJECTED,
                        message=msg,
                        recipient_student=ch.created_by_student,
                        sender_user=request.user,
                        challenge=ch,
                    )
                except Exception:
                    logger.exception("challenge reject notify")
        else:
            initiator = ch.created_by_student
            if not initiator:
                return Response({"detail": "Başlatıcı öğrenci bulunamadı."}, status=status.HTTP_400_BAD_REQUEST)
            if ch.ends_at and ch.ends_at <= now:
                return Response(
                    {
                        "detail": "Önerilen bitiş zamanı geçmiş. Öğrencinin başlangıç ve bitiş tarihlerini güncelleyerek yeniden önermesi gerekir."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                ch.status = KidsChallenge.Status.ACTIVE
                ch.reviewed_at = now
                ch.reviewed_by = request.user
                ch.activated_at = now
                ch.save(
                    update_fields=["status", "reviewed_at", "reviewed_by", "activated_at", "updated_at"]
                )
                _, chm_created = KidsChallengeMember.objects.get_or_create(
                    challenge=ch,
                    student=initiator,
                    defaults={"is_initiator": True},
                )
                on_challenge_member_created(initiator.pk, chm_created)
            _lang = language_for_kids_student(initiator)
            msg = translate(_lang, "kids.notif.challenge_approved_student", title=ch.title)
            try:
                create_kids_notification(
                    notification_type=KidsNotification.NotificationType.CHALLENGE_APPROVED,
                    message=msg,
                    recipient_student=initiator,
                    sender_user=request.user,
                    challenge=ch,
                )
            except Exception:
                logger.exception("challenge approve notify")
        ch = KidsChallenge.objects.select_related("kids_class").prefetch_related("members__student").get(pk=ch.pk)
        return Response(KidsChallengeReadSerializer(ch, context={"request": request}).data)


def _parent_free_challenge_item_dict(ch: KidsChallenge, request) -> dict:
    ser_ctx = {"request": request}
    st = ch.created_by_student
    return {
        "challenge": KidsChallengeReadSerializer(ch, context=ser_ctx).data,
        "child": (
            {
                "id": st.id,
                "first_name": st.first_name,
                "last_name": st.last_name,
            }
            if st
            else None
        ),
    }


def parent_free_challenges_overview_for_user(request) -> dict:
    """Veli kullanıcısı için bekleyen + velinin karar verdiği serbest yarışmalar."""
    user = request.user
    base = (
        KidsChallenge.objects.filter(
            peer_scope=KidsChallenge.PeerScope.FREE_PARENT,
            source=KidsChallenge.Source.STUDENT,
            created_by_student__parent_account=user,
        )
        .select_related("kids_class", "created_by_student")
        .prefetch_related("members__student")
    )
    pending_qs = base.filter(status=KidsChallenge.Status.PENDING_PARENT).order_by("-created_at")
    history_qs = (
        base.filter(
            reviewed_by=user,
            status__in=[
                KidsChallenge.Status.ACTIVE,
                KidsChallenge.Status.ENDED,
                KidsChallenge.Status.REJECTED,
            ],
        )
        .order_by(F("reviewed_at").desc(nulls_last=True), "-id")[:200]
    )
    return {
        "pending": [_parent_free_challenge_item_dict(c, request) for c in pending_qs],
        "history": [_parent_free_challenge_item_dict(c, request) for c in history_qs],
    }


class KidsParentFreeChallengesOverviewView(KidsAuthenticatedMixin, APIView):
    """Veli: bekleyen ve geçmiş (onay / red) serbest yarışmalar tek yanıtta."""

    permission_classes = [IsAuthenticated, IsKidsParent]

    def get(self, request):
        return Response(parent_free_challenges_overview_for_user(request))


class KidsParentPendingFreeChallengesView(KidsAuthenticatedMixin, APIView):
    """Geriye dönük: yalnızca bekleyen liste (`items`)."""

    permission_classes = [IsAuthenticated, IsKidsParent]

    def get(self, request):
        data = parent_free_challenges_overview_for_user(request)
        return Response({"items": data["pending"]})


class KidsParentFreeChallengeReviewView(KidsAuthenticatedMixin, APIView):
    permission_classes = [IsAuthenticated, IsKidsParent]

    def post(self, request, pk):
        try:
            ch = KidsChallenge.objects.select_related("kids_class", "created_by_student").get(
                pk=pk,
                peer_scope=KidsChallenge.PeerScope.FREE_PARENT,
                source=KidsChallenge.Source.STUDENT,
                status=KidsChallenge.Status.PENDING_PARENT,
                created_by_student__parent_account=request.user,
            )
        except KidsChallenge.DoesNotExist:
            return Response(
                {"detail": "Yarışma bulunamadı veya bu çocuğun bekleyen serbest önerisi değil."},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = KidsParentFreeChallengeReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        decision = ser.validated_data["decision"]
        now = timezone.now()
        if decision == "reject":
            note = (ser.validated_data.get("rejection_note") or "").strip()[:600]
            with transaction.atomic():
                ch.status = KidsChallenge.Status.REJECTED
                ch.parent_rejection_note = note
                ch.reviewed_at = now
                ch.reviewed_by = request.user
                ch.save(
                    update_fields=[
                        "status",
                        "parent_rejection_note",
                        "reviewed_at",
                        "reviewed_by",
                        "updated_at",
                    ]
                )
            if ch.created_by_student:
                _lang = language_for_kids_student(ch.created_by_student)
                base = translate(_lang, "kids.notif.challenge_rejected_parent", title=ch.title)
                msg = (
                    translate(_lang, "kids.notif.challenge_rejected_parent_note", base=base, note=note)
                    if note
                    else base
                )
                try:
                    create_kids_notification(
                        notification_type=KidsNotification.NotificationType.CHALLENGE_REJECTED,
                        message=msg,
                        recipient_student=ch.created_by_student,
                        sender_user=request.user,
                        challenge=ch,
                    )
                except Exception:
                    logger.exception("free challenge parent reject notify")
        else:
            initiator = ch.created_by_student
            if not initiator:
                return Response({"detail": "Başlatıcı öğrenci bulunamadı."}, status=status.HTTP_400_BAD_REQUEST)
            if ch.ends_at and ch.ends_at <= now:
                return Response(
                    {
                        "detail": "Önerilen bitiş zamanı geçmiş. Çocuğun başlangıç ve bitiş tarihlerini güncelleyerek yeniden önermesi gerekir."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                ch.status = KidsChallenge.Status.ACTIVE
                ch.reviewed_at = now
                ch.reviewed_by = request.user
                ch.activated_at = now
                ch.save(
                    update_fields=["status", "reviewed_at", "reviewed_by", "activated_at", "updated_at"]
                )
                _, chm_created = KidsChallengeMember.objects.get_or_create(
                    challenge=ch,
                    student=initiator,
                    defaults={"is_initiator": True},
                )
                on_challenge_member_created(initiator.pk, chm_created)
            _lang = language_for_kids_student(initiator)
            msg = translate(_lang, "kids.notif.challenge_approved_free", title=ch.title)
            try:
                create_kids_notification(
                    notification_type=KidsNotification.NotificationType.CHALLENGE_APPROVED,
                    message=msg,
                    recipient_student=initiator,
                    sender_user=request.user,
                    challenge=ch,
                )
            except Exception:
                logger.exception("free challenge parent approve notify")
        ch = KidsChallenge.objects.select_related("kids_class").prefetch_related("members__student").get(pk=ch.pk)
        return Response(KidsChallengeReadSerializer(ch, context={"request": request}).data)
