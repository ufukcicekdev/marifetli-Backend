"""Öğrenci rozetleri: yol haritası (milestone) + proje yıldızı (öğretmen seçimi)."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    KidsChallengeMember,
    KidsFreestylePost,
    KidsGameSession,
    KidsHomeworkSubmission,
    KidsSubmission,
    KidsTestAttempt,
    KidsUser,
    KidsUserBadge,
    KidsUserRole,
)

# Proje başına en fazla “yıldız” seçimi (öğrenci sayısından bağımsız üst sınır).
MAX_TEACHER_PICKS_PER_ASSIGNMENT = 5

# İlk kez yıldız seçildiğinde ek büyüme puanı (bir kez / proje / öğrenci).
TEACHER_PICK_GROWTH_BONUS = 5

# Tek seferlik aktivite puanları (growth_points; rozet eşiklerine de girer).
HOMEWORK_FIRST_MARK_DONE_GP = 1
CHALLENGE_MEMBERSHIP_JOIN_GP = 1
TEST_FIRST_SUBMIT_GP = 2
FREESTYLE_POST_CREATE_GP = 2

# --- Yol haritası: tek kaynak (sıra, görünüm, rozet anahtarı, kural) ---
# rule: None = yalnızca ensure_first_submit / dış mantık (first_submit).
# Diğerleri: (metrik_adi, minimum_sayi)
ROADMAP_MILESTONE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "first_submit",
        "order": 0,
        "icon": "seed",
        "title": "İlk adım",
        "subtitle": "İlk proje teslimin.",
        "label": "İlk adım",
        "rule": None,
    },
    {
        "key": "growth_6",
        "order": 1,
        "icon": "sprout",
        "title": "Filiz",
        "subtitle": "Büyüme puanın 6’ya ulaştı.",
        "label": "Filiz rozeti",
        "rule": ("growth_points", 6),
    },
    {
        "key": "hw_done_1",
        "order": 2,
        "icon": "book",
        "title": "Ödev disiplini",
        "subtitle": "İlk ödevini tamamladın.",
        "label": "Ödev: ilk adım",
        "rule": ("homework_marked_done", 1),
    },
    {
        "key": "proj_sub_3",
        "order": 3,
        "icon": "tree",
        "title": "Üçlü çaba",
        "subtitle": "3 proje teslimi.",
        "label": "3 proje teslimi",
        "rule": ("project_submissions", 3),
    },
    {
        "key": "challenge_1",
        "order": 4,
        "icon": "flag",
        "title": "Yarışmacı",
        "subtitle": "Bir yarışmaya katıldın.",
        "label": "İlk yarışma",
        "rule": ("challenge_memberships", 1),
    },
    {
        "key": "growth_16",
        "order": 5,
        "icon": "tree",
        "title": "Gelişen",
        "subtitle": "Büyüme puanın 16’ya ulaştı.",
        "label": "Gelişen yol",
        "rule": ("growth_points", 16),
    },
    {
        "key": "pick_1",
        "order": 6,
        "icon": "medal_pick",
        "title": "Parlayan an",
        "subtitle": "Öğretmen yıldızın oldu.",
        "label": "İlk proje yıldızı",
        "rule": ("teacher_pick_badges", 1),
    },
    {
        "key": "hw_done_5",
        "order": 7,
        "icon": "book",
        "title": "Ödev rutini",
        "subtitle": "5 ödev tamamladın.",
        "label": "5 ödev",
        "rule": ("homework_marked_done", 5),
    },
    {
        "key": "game_first_complete",
        "order": 8,
        "icon": "gamepad",
        "title": "Oyun kurdu",
        "subtitle": "İlk oyununu bitirdin.",
        "label": "İlk oyun tamamlandı",
        "rule": ("game_sessions_completed", 1),
    },
    {
        "key": "growth_30",
        "order": 9,
        "icon": "star_tree",
        "title": "Parlayan",
        "subtitle": "Büyüme puanın 30’a ulaştı.",
        "label": "Parlayan",
        "rule": ("growth_points", 30),
    },
    {
        "key": "test_1",
        "order": 10,
        "icon": "flask",
        "title": "Bilim yolcusu",
        "subtitle": "İlk testini gönderdin.",
        "label": "İlk test",
        "rule": ("tests_submitted", 1),
    },
    {
        "key": "proj_sub_10",
        "order": 11,
        "icon": "tree",
        "title": "Onluk seri",
        "subtitle": "10 proje teslimi.",
        "label": "10 proje teslimi",
        "rule": ("project_submissions", 10),
    },
    {
        "key": "hw_done_10",
        "order": 12,
        "icon": "book",
        "title": "Ödev ustası",
        "subtitle": "10 ödev tamamladın.",
        "label": "10 ödev",
        "rule": ("homework_marked_done", 10),
    },
    {
        "key": "challenge_5",
        "order": 13,
        "icon": "flag",
        "title": "Arena",
        "subtitle": "5 yarışmada yer aldın.",
        "label": "5 yarışma",
        "rule": ("challenge_memberships", 5),
    },
    {
        "key": "growth_50",
        "order": 14,
        "icon": "star_tree",
        "title": "Yükselen enerji",
        "subtitle": "Büyüme puanın 50’ye ulaştı.",
        "label": "50 büyüme puanı",
        "rule": ("growth_points", 50),
    },
    {
        "key": "game_five_complete",
        "order": 15,
        "icon": "gamepad",
        "title": "Oyuncu",
        "subtitle": "5 oyun tamamladın.",
        "label": "5 oyun tamamlandı",
        "rule": ("game_sessions_completed", 5),
    },
    {
        "key": "pick_5",
        "order": 16,
        "icon": "medal_pick",
        "title": "Yıldız yağmuru",
        "subtitle": "5 proje yıldızı topladın.",
        "label": "5 proje yıldızı",
        "rule": ("teacher_pick_badges", 5),
    },
    {
        "key": "proj_sub_25",
        "order": 17,
        "icon": "tree",
        "title": "Üretken",
        "subtitle": "25 proje teslimi.",
        "label": "25 proje teslimi",
        "rule": ("project_submissions", 25),
    },
    {
        "key": "hw_done_25",
        "order": 18,
        "icon": "book",
        "title": "Ödev şampiyonu",
        "subtitle": "25 ödev tamamladın.",
        "label": "25 ödev",
        "rule": ("homework_marked_done", 25),
    },
    {
        "key": "test_10",
        "order": 19,
        "icon": "flask",
        "title": "Test koleksiyoncusu",
        "subtitle": "10 test gönderdin.",
        "label": "10 test",
        "rule": ("tests_submitted", 10),
    },
    {
        "key": "growth_80",
        "order": 20,
        "icon": "star_tree",
        "title": "Işık hızı",
        "subtitle": "Büyüme puanın 80’e ulaştı.",
        "label": "80 büyüme puanı",
        "rule": ("growth_points", 80),
    },
    {
        "key": "freestyle_1",
        "order": 21,
        "icon": "gallery",
        "title": "Kürsü",
        "subtitle": "Serbest kürsüde ilk paylaşımın.",
        "label": "İlk kürsü paylaşımı",
        "rule": ("freestyle_posts", 1),
    },
)

ROADMAP_MILESTONES: tuple[dict, ...] = tuple(
    {k: v for k, v in spec.items() if k not in ("rule", "label")} for spec in ROADMAP_MILESTONE_SPECS
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


def add_student_growth_points(student_id: int, delta: int) -> None:
    if delta <= 0:
        return
    KidsUser.objects.filter(pk=student_id, role=KidsUserRole.STUDENT).update(
        growth_points=F("growth_points") + delta
    )


def try_award_first_submit_badge(student_id: int) -> None:
    u = KidsUser.objects.filter(pk=student_id).only("role").first()
    if not u or u.role != KidsUserRole.STUDENT:
        return
    if KidsSubmission.objects.filter(student_id=student_id).count() != 1:
        return
    try_award_badge(student_id, "first_submit", "İlk adım")


def ensure_first_submit_badge(student_id: int) -> None:
    """En az bir teslim varsa `first_submit` rozetini ver (eski veri / kaçırılan anlar için)."""
    u = KidsUser.objects.filter(pk=student_id).only("role").first()
    if not u or u.role != KidsUserRole.STUDENT:
        return
    if KidsUserBadge.objects.filter(student_id=student_id, key="first_submit").exists():
        return
    if KidsSubmission.objects.filter(student_id=student_id).exists():
        try_award_badge(student_id, "first_submit", "İlk adım")


def _teacher_pick_badge_count(student_id: int) -> int:
    n = 0
    prefix = "teacher_pick_"
    for k in KidsUserBadge.objects.filter(student_id=student_id).values_list("key", flat=True):
        if k.startswith(prefix) and k[len(prefix) :].isdigit():
            n += 1
    return n


def compute_student_badge_metrics(student_id: int) -> dict[str, int]:
    """Rozet kuralları için sayımlar (tek yerden doğruluk)."""
    homework_marked_done = KidsHomeworkSubmission.objects.filter(
        student_id=student_id,
        student_done_at__isnull=False,
    ).count()
    project_submissions = KidsSubmission.objects.filter(student_id=student_id).count()
    challenge_memberships = KidsChallengeMember.objects.filter(student_id=student_id).count()
    game_sessions_completed = KidsGameSession.objects.filter(
        student_id=student_id,
        status=KidsGameSession.SessionStatus.COMPLETED,
    ).count()
    tests_submitted = KidsTestAttempt.objects.filter(
        student_id=student_id,
        submitted_at__isnull=False,
    ).count()
    freestyle_posts = KidsFreestylePost.objects.filter(student_id=student_id).count()
    return {
        "homework_marked_done": homework_marked_done,
        "project_submissions": project_submissions,
        "challenge_memberships": challenge_memberships,
        "game_sessions_completed": game_sessions_completed,
        "tests_submitted": tests_submitted,
        "freestyle_posts": freestyle_posts,
        "teacher_pick_badges": _teacher_pick_badge_count(student_id),
    }


def _rule_satisfied(
    rule: tuple[str, int] | None,
    growth_points: int,
    metrics: dict[str, int],
) -> bool:
    if rule is None:
        return False
    kind, need = rule
    if kind == "growth_points":
        return growth_points >= need
    return int(metrics.get(kind, 0)) >= need


def sync_all_milestone_badges(student_id: int) -> None:
    """Tüm yol haritası rozetlerini güncel metrik ve puana göre ver."""
    u = KidsUser.objects.filter(pk=student_id).only("growth_points", "role").first()
    if not u or u.role != KidsUserRole.STUDENT:
        return
    metrics = compute_student_badge_metrics(student_id)
    gp = int(u.growth_points or 0)
    earned = set(KidsUserBadge.objects.filter(student_id=student_id).values_list("key", flat=True))
    for spec in ROADMAP_MILESTONE_SPECS:
        key = spec["key"]
        if key in earned:
            continue
        rule = spec.get("rule")
        if rule is None:
            continue
        if _rule_satisfied(rule, gp, metrics):
            try_award_badge(student_id, key, spec["label"])


def sync_growth_milestone_badges(student_id: int) -> None:
    """Geriye dönük uyumluluk: tüm milestone senkronu."""
    sync_all_milestone_badges(student_id)


def on_challenge_member_created(student_id: int, created: bool) -> None:
    if not created:
        return
    add_student_growth_points(student_id, CHALLENGE_MEMBERSHIP_JOIN_GP)
    sync_all_milestone_badges(student_id)


def _compute_next_milestone_progress(
    milestones: list[dict],
    gp: int,
    metrics: dict[str, int],
) -> dict | None:
    """
    Sıradaki (ilk kilitli) kilometre taşına göre ilerleme.
    Dönüş: { key, current, target, percent } veya tümü açıksa None.
    """
    spec_by_key = {s["key"]: s for s in ROADMAP_MILESTONE_SPECS}
    ordered = sorted(milestones, key=lambda x: int(x.get("order", 0)))
    for m in ordered:
        if m.get("unlocked"):
            continue
        key = m["key"]
        spec = spec_by_key.get(key)
        if not spec:
            continue
        rule = spec.get("rule")
        if rule is None:
            cur = int(metrics.get("project_submissions", 0))
            tgt = 1
            pct = min(100, max(0, int(round(100 * cur / tgt)))) if tgt else 0
            return {"key": key, "current": cur, "target": tgt, "percent": pct}

        kind, need = rule
        tgt = int(need)
        if kind == "growth_points":
            cur = int(gp)
        else:
            cur = int(metrics.get(kind, 0))
        if tgt <= 0:
            pct = 100
        else:
            pct = min(100, max(0, int(round(100 * cur / tgt))))
        return {"key": key, "current": cur, "target": tgt, "percent": pct}
    return None


def build_student_roadmap(user: KidsUser) -> dict:
    """Öğrenci için Duolingo tarzı yol verisi (API)."""
    if user.role != KidsUserRole.STUDENT:
        return {"milestones": [], "teacher_picks": [], "growth_points": 0, "next_milestone_progress": None}

    ensure_first_submit_badge(user.id)
    sync_all_milestone_badges(user.id)
    user.refresh_from_db(fields=["growth_points"])

    earned = {
        b.key: {"earned_at": b.earned_at.isoformat(), "label": b.label}
        for b in KidsUserBadge.objects.filter(student=user).order_by("earned_at")
    }
    gp = int(user.growth_points or 0)
    metrics = compute_student_badge_metrics(user.id)

    milestones = []
    for m in ROADMAP_MILESTONES:
        key = m["key"]
        row = {**m, "unlocked": key in earned, "earned_at": None}
        if key in earned:
            row["earned_at"] = earned[key]["earned_at"]
        milestones.append(row)

    next_milestone_progress = _compute_next_milestone_progress(milestones, gp, metrics)

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
        "next_milestone_progress": next_milestone_progress,
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
        sync_all_milestone_badges(student.id)
    return locked, new_badge
