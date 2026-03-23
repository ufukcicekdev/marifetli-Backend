"""Öğrenci rozetleri: yol haritası (milestone) + proje yıldızı (öğretmen seçimi)."""

from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import KidsSubmission, KidsUser, KidsUserBadge, KidsUserRole

# Proje başına en fazla “yıldız” seçimi (öğrenci sayısından bağımsız üst sınır).
MAX_TEACHER_PICKS_PER_ASSIGNMENT = 5

# İlk kez yıldız seçildiğinde ek büyüme puanı (bir kez / proje / öğrenci).
TEACHER_PICK_GROWTH_BONUS = 5

# Büyüme puanına göre otomatik rozet eşikleri (puan >= eşik).
GROWTH_MILESTONE_BADGES: tuple[tuple[int, str, str], ...] = (
    (6, "growth_6", "Filiz rozeti"),
    (16, "growth_16", "Gelişen yol"),
    (30, "growth_30", "Parlayan"),
)

# Yol haritası sırası (sabit düğümler; proje yıldızları ayrı liste).
ROADMAP_MILESTONES: tuple[dict, ...] = (
    {
        "key": "first_submit",
        "order": 0,
        "icon": "seed",
        "title": "İlk adım",
        "subtitle": "İlk projeni teslim ettin.",
    },
    {
        "key": "growth_6",
        "order": 1,
        "icon": "sprout",
        "title": "Filiz",
        "subtitle": "Büyüme puanın 6’ya ulaştı.",
    },
    {
        "key": "growth_16",
        "order": 2,
        "icon": "tree",
        "title": "Gelişen",
        "subtitle": "Büyüme puanın 16’ya ulaştı.",
    },
    {
        "key": "growth_30",
        "order": 3,
        "icon": "star_tree",
        "title": "Parlayan",
        "subtitle": "Büyüme puanın 30’a ulaştı.",
    },
)


def badge_key_teacher_pick(assignment_id: int) -> str:
    return f"teacher_pick_{assignment_id}"


def try_award_badge(student_id: int, key: str, label: str) -> bool:
    """True = yeni rozet oluşturuldu."""
    if not key:
        return False
    _, created = KidsUserBadge.objects.get_or_create(
        student_id=student_id,
        key=key,
        defaults={"label": label[:200]},
    )
    return created


def try_award_first_submit_badge(student_id: int) -> None:
    u = KidsUser.objects.filter(pk=student_id).only("role").first()
    if not u or u.role != KidsUserRole.STUDENT:
        return
    if KidsSubmission.objects.filter(student_id=student_id).count() != 1:
        return
    try_award_badge(student_id, "first_submit", "İlk adım")


def sync_growth_milestone_badges(student_id: int) -> None:
    u = KidsUser.objects.filter(pk=student_id).only("growth_points", "role").first()
    if not u or u.role != KidsUserRole.STUDENT:
        return
    p = int(u.growth_points or 0)
    for threshold, key, label in GROWTH_MILESTONE_BADGES:
        if p >= threshold:
            try_award_badge(student_id, key, label)


def build_student_roadmap(user: KidsUser) -> dict:
    """Öğrenci için Duolingo tarzı yol verisi (API)."""
    if user.role != KidsUserRole.STUDENT:
        return {"milestones": [], "teacher_picks": [], "growth_points": 0}

    earned = {
        b.key: {"earned_at": b.earned_at.isoformat(), "label": b.label}
        for b in KidsUserBadge.objects.filter(student=user).order_by("earned_at")
    }
    gp = int(user.growth_points or 0)

    milestones = []
    for m in ROADMAP_MILESTONES:
        key = m["key"]
        row = {**m, "unlocked": key in earned, "earned_at": None}
        if key in earned:
            row["earned_at"] = earned[key]["earned_at"]
        milestones.append(row)

    picks = []
    prefix = "teacher_pick_"
    for key, meta in earned.items():
        if key.startswith(prefix):
            rest = key[len(prefix) :]
            if rest.isdigit():
                picks.append(
                    {
                        "key": key,
                        "assignment_id": int(rest),
                        "label": meta.get("label") or "Proje yıldızı",
                        "earned_at": meta["earned_at"],
                    }
                )
    picks.sort(key=lambda x: x["earned_at"])

    return {
        "milestones": milestones,
        "teacher_picks": picks,
        "growth_points": gp,
        "teacher_pick_limit": MAX_TEACHER_PICKS_PER_ASSIGNMENT,
    }


def apply_teacher_pick(
    submission: KidsSubmission,
    want_pick: bool,
) -> tuple[KidsSubmission, bool]:
    """
    Öğretmen yıldızı. Rozet ve bonus puan yalnızca ilk seçimde (sticky rozet).
    Dönüş: (güncellenmiş kayıt, yeni_rozet_kazanıldı_mı)
    """
    student = submission.student
    if student.role != KidsUserRole.STUDENT:
        raise ValueError("Yalnızca öğrenci teslimleri işaretlenebilir.")

    new_badge = False
    with transaction.atomic():
        locked = (
            KidsSubmission.objects.select_for_update()
            .filter(pk=submission.pk)
            .select_related("assignment", "student")
            .first()
        )
        if not locked:
            raise ValueError("Teslim bulunamadı.")

        if want_pick:
            if locked.is_teacher_pick:
                return locked, False
            n = KidsSubmission.objects.filter(
                assignment_id=locked.assignment_id,
                is_teacher_pick=True,
            ).count()
            if n >= MAX_TEACHER_PICKS_PER_ASSIGNMENT:
                raise ValueError(
                    f"Bu projede en fazla {MAX_TEACHER_PICKS_PER_ASSIGNMENT} yıldız seçilebilir."
                )
            locked.is_teacher_pick = True
            locked.teacher_picked_at = timezone.now()
            locked.save(update_fields=["is_teacher_pick", "teacher_picked_at", "updated_at"])

            title = (locked.assignment.title or "Proje")[:120]
            key = badge_key_teacher_pick(locked.assignment_id)
            if try_award_badge(student.id, key, f"Proje yıldızı: {title}"):
                KidsUser.objects.filter(pk=student.id).update(
                    growth_points=F("growth_points") + TEACHER_PICK_GROWTH_BONUS
                )
                new_badge = True
        else:
            if not locked.is_teacher_pick:
                return locked, False
            locked.is_teacher_pick = False
            locked.teacher_picked_at = None
            locked.save(update_fields=["is_teacher_pick", "teacher_picked_at", "updated_at"])

    locked.refresh_from_db()
    if new_badge:
        sync_growth_milestone_badges(student.id)
    return locked, new_badge
