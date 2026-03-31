"""
Sınıf challenge kuralları: aylık öğrenci başlatma, tek aktif üyelik, öğretmen yarışması önceliği.
"""
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    KidsChallenge,
    KidsChallengeInvite,
    KidsChallengeMember,
    KidsClass,
    KidsEnrollment,
    KidsUser,
    KidsUserRole,
)


def month_start(dt: datetime | None = None) -> datetime:
    d = dt or timezone.now()
    return d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def student_enrolled_in_class(student_id: int, class_id: int) -> bool:
    return KidsEnrollment.objects.filter(student_id=student_id, kids_class_id=class_id).exists()


def active_memberships_for_student_in_class(student_id: int, class_id: int):
    return KidsChallengeMember.objects.filter(
        student_id=student_id,
        challenge__kids_class_id=class_id,
        challenge__status=KidsChallenge.Status.ACTIVE,
    ).select_related("challenge")


def student_has_active_challenge_in_class(student_id: int, class_id: int) -> bool:
    return active_memberships_for_student_in_class(student_id, class_id).exists()


def count_student_challenge_starts_in_window(student_id: int, class_id: int) -> int:
    """Öğrencinin bu sınıfta başlattığı (STUDENT kaynaklı) challenge sayısı — ay veya gün penceresi settings’ten."""
    qs = KidsChallenge.objects.filter(
        source=KidsChallenge.Source.STUDENT,
        created_by_student_id=student_id,
        kids_class_id=class_id,
    )
    interval_days = max(0, int(getattr(settings, "KIDS_CHALLENGE_STUDENT_START_INTERVAL_DAYS", 0) or 0))
    if interval_days <= 0:
        qs = qs.filter(created_at__gte=month_start())
    else:
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=interval_days))
    return qs.count()


def can_propose_student_challenge(student: KidsUser, kids_class: KidsClass) -> tuple[bool, str]:
    if student.role != KidsUserRole.STUDENT:
        return False, "Yalnızca öğrenci hesapları yarışma önerebilir."
    if not student_enrolled_in_class(student.pk, kids_class.pk):
        return False, "Bu sınıfta kayıtlı değilsin."
    if student_has_active_challenge_in_class(student.pk, kids_class.pk):
        return False, "Bu sınıfta zaten devam eden bir yarışmaya katılıyorsun; yeni öneri veya davet için önce onu tamamlamalısın."
    if getattr(settings, "KIDS_CHALLENGE_STUDENT_START_LIMIT_ENABLED", True):
        max_starts = int(getattr(settings, "KIDS_CHALLENGE_STUDENT_MAX_STARTS_PER_WINDOW", 1) or 1)
        if max_starts < 1:
            max_starts = 1
        n = count_student_challenge_starts_in_window(student.pk, kids_class.pk)
        if n >= max_starts:
            interval_days = max(0, int(getattr(settings, "KIDS_CHALLENGE_STUDENT_START_INTERVAL_DAYS", 0) or 0))
            if interval_days <= 0:
                if max_starts == 1:
                    return (
                        False,
                        "Bu sınıfta bu ay zaten bir yarışma önerdin. Ay başında tekrar deneyebilirsin.",
                    )
                return (
                    False,
                    f"Bu sınıfta bu ay en fazla {max_starts} yarışma önerebilirsin.",
                )
            if max_starts == 1:
                return (
                    False,
                    f"Bu sınıfta son {interval_days} gün içinde zaten bir yarışma önerdin. Bir süre sonra tekrar deneyebilirsin.",
                )
            return (
                False,
                f"Bu sınıfta son {interval_days} günde en fazla {max_starts} yarışma önerebilirsin.",
            )
    return True, ""


def ensure_challenge_time_state(ch: KidsChallenge) -> None:
    """
    Öğrenci kaynaklı aktif yarışmada `ends_at` geçtiyse otomatik sonlandır.
    """
    if ch.status != KidsChallenge.Status.ACTIVE:
        return
    if ch.source != KidsChallenge.Source.STUDENT:
        return
    if not ch.ends_at:
        return
    if timezone.now() <= ch.ends_at:
        return
    ch.status = KidsChallenge.Status.ENDED
    ch.ended_at = timezone.now()
    ch.save(update_fields=["status", "ended_at", "updated_at"])


def peer_student_challenge_actions_allowed(ch: KidsChallenge) -> tuple[bool, str]:
    """
    Öğrenci yarışmasında davet gönderme / daveti kabul: zaman penceresi açık mı?
    Çağıran önce `ensure_challenge_time_state(ch)` çalıştırmalı (süresi dolmuşsa sonlandırır).
    Eski kayıtlarda starts_at/ends_at boş olabilir → kısıt yok.
    """
    if ch.status != KidsChallenge.Status.ACTIVE:
        return False, "Bu yarışma artık aktif değil."
    if ch.source != KidsChallenge.Source.STUDENT:
        return True, ""
    now = timezone.now()
    if ch.starts_at and now < ch.starts_at:
        return False, "Yarışma henüz başlamadı; bu işlem için başlangıç zamanını bekleyin."
    if ch.ends_at and now > ch.ends_at:
        return False, "Yarışma süresi sona erdi."
    return True, ""


def can_accept_peer_invite(invitee: KidsUser, challenge: KidsChallenge) -> tuple[bool, str]:
    """Öğretmen kaynaklı yarışmada aynı sınıfta başka aktif üyelik olsa da kabul edilebilir (davet sonrası temizlenir)."""
    if challenge.source != KidsChallenge.Source.STUDENT:
        return True, ""
    if not challenge.kids_class_id:
        return True, ""
    other = active_memberships_for_student_in_class(invitee.pk, challenge.kids_class_id).exclude(
        challenge_id=challenge.pk
    )
    if other.exists():
        return (
            False,
            "Bu sınıfta başka bir arkadaş yarışmasına katılıyorsun; önce onu bitirmeden bu daveti kabul edemezsin.",
        )
    return True, ""


def count_free_parent_challenge_starts_in_window(student_id: int) -> int:
    """Serbest (veli onaylı) öğrenci yarışması öneri sayısı — ay veya gün penceresi settings ile sınıf akışıyla aynı."""
    qs = KidsChallenge.objects.filter(
        source=KidsChallenge.Source.STUDENT,
        created_by_student_id=student_id,
        peer_scope=KidsChallenge.PeerScope.FREE_PARENT,
    )
    interval_days = max(0, int(getattr(settings, "KIDS_CHALLENGE_STUDENT_START_INTERVAL_DAYS", 0) or 0))
    if interval_days <= 0:
        qs = qs.filter(created_at__gte=month_start())
    else:
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=interval_days))
    return qs.count()


def can_propose_free_parent_challenge(student: KidsUser) -> tuple[bool, str]:
    if student.role != KidsUserRole.STUDENT:
        return False, "Yalnızca öğrenci hesapları yarışma önerebilir."
    if not student.parent_account_id:
        return (
            False,
            "Serbest yarışma için veli hesabının çocuk profiline bağlı olması gerekir. "
            "Öğretmen veya okul davetiyle veli bağlantısı yapılabilir.",
        )
    if KidsChallenge.objects.filter(
        created_by_student_id=student.pk,
        peer_scope=KidsChallenge.PeerScope.FREE_PARENT,
        status=KidsChallenge.Status.PENDING_PARENT,
    ).exists():
        return (
            False,
            "Veli onayı bekleyen bir serbest yarışman var; onaylandıktan veya reddedildikten sonra yenisini önerebilirsin.",
        )
    if KidsChallenge.objects.filter(
        created_by_student_id=student.pk,
        peer_scope=KidsChallenge.PeerScope.FREE_PARENT,
        status=KidsChallenge.Status.ACTIVE,
    ).exists():
        return False, "Zaten devam eden bir serbest yarışman var; önce onu tamamlamalısın."
    if getattr(settings, "KIDS_CHALLENGE_STUDENT_START_LIMIT_ENABLED", True):
        max_starts = int(getattr(settings, "KIDS_CHALLENGE_STUDENT_MAX_STARTS_PER_WINDOW", 1) or 1)
        if max_starts < 1:
            max_starts = 1
        n = count_free_parent_challenge_starts_in_window(student.pk)
        if n >= max_starts:
            interval_days = max(0, int(getattr(settings, "KIDS_CHALLENGE_STUDENT_START_INTERVAL_DAYS", 0) or 0))
            if interval_days <= 0:
                if max_starts == 1:
                    return (
                        False,
                        "Bu ay zaten bir serbest yarışma önerdin. Ay başında tekrar deneyebilirsin.",
                    )
                return False, f"Bu ay en fazla {max_starts} serbest yarışma önerebilirsin."
            if max_starts == 1:
                return (
                    False,
                    f"Son {interval_days} gün içinde zaten bir serbest yarışma önerdin. Bir süre sonra tekrar deneyebilirsin.",
                )
            return False, f"Son {interval_days} günde en fazla {max_starts} serbest yarışma önerebilirsin."
    return True, ""


@transaction.atomic
def clear_student_peer_active_memberships_except(student_id: int, class_id: int, keep_challenge_id: int) -> None:
    """Öğretmen üye eklerken: aynı sınıftaki diğer aktif üyelikleri kaldır (öğretmen yarışması öncelikli)."""
    qs = KidsChallengeMember.objects.select_related("challenge").filter(
        student_id=student_id,
        challenge__kids_class_id=class_id,
        challenge__status=KidsChallenge.Status.ACTIVE,
        challenge__source=KidsChallenge.Source.STUDENT,
    ).exclude(challenge_id=keep_challenge_id)
    challenge_ids = set()
    for m in qs:
        challenge_ids.add(m.challenge_id)
    qs.delete()
    for cid in challenge_ids:
        ch = KidsChallenge.objects.filter(pk=cid).first()
        if ch and not ch.members.exists():
            ch.status = KidsChallenge.Status.ENDED
            ch.ended_at = timezone.now()
            ch.save(update_fields=["status", "ended_at", "updated_at"])


def build_invite_notification_message(
    inviter: KidsUser,
    challenge: KidsChallenge,
    *,
    personal_message: str,
    lang: str = "tr",
) -> str:
    from core.i18n_catalog import random_invite_motivation, translate
    from core.i18n_catalog import normalize_lang

    lang = normalize_lang(lang)
    who = inviter.full_name or inviter.email.split("@")[0]
    title = challenge.title
    tail = random_invite_motivation(lang)
    extra = (personal_message or "").strip()
    if extra:
        return translate(
            lang,
            "kids.notif.invite_personal",
            who=who,
            title=title,
            extra=extra,
            tail=tail,
        )
    return translate(lang, "kids.notif.invite_line1", who=who, title=title) + "\n\n" + tail
