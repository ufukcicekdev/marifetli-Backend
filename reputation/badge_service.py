"""
Davranışa dayalı rozetler (itibar puanı akışını değiştirmez).
"""
from __future__ import annotations

import logging
from typing import Optional

from django.contrib.auth import get_user_model

from .models import Badge, UserBadge

User = get_user_model()
logger = logging.getLogger(__name__)

SLUG_WELCOME = 'hos-geldin'
SLUG_HELPFUL = 'yardimsever'
SLUG_MASTER_SHARER = 'usta-paylasic'
SLUG_POPULAR = 'popular'


def _grant_badge(user: User, slug: str) -> bool:
    """Rozet yoksa oluşturur. Yeni verildiyse True."""
    try:
        badge = Badge.objects.get(slug=slug)
    except Badge.DoesNotExist:
        logger.warning('badge_service: rozet bulunamadı slug=%s', slug)
        return False
    _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    return created


class BadgeService:
    """Profil görseli, cevap sayısı, tasarım ve popülerlik rozetleri."""

    @staticmethod
    def _user_has_any_avatar(user: User) -> bool:
        if getattr(user, 'profile_picture', None):
            return True
        try:
            return bool(user.profile.avatar)
        except Exception:
            return False

    @classmethod
    def on_profile_media_updated(cls, user: User) -> bool:
        """İlk profil fotoğrafı (User veya UserProfile.avatar)."""
        if not user or not user.pk:
            return False
        if not cls._user_has_any_avatar(user):
            return False
        return _grant_badge(user, SLUG_WELCOME)

    @classmethod
    def try_helpful_badge_for_user(cls, user: User) -> bool:
        """Onaylı cevap sayısı yeterliyse Yardımsever verir (yeni ise True)."""
        if not user or not user.pk:
            return False
        badge = Badge.objects.filter(slug=SLUG_HELPFUL).first()
        need = badge.requirement_value if badge else 10
        from answers.models import Answer

        count = Answer.objects.filter(
            author=user,
            is_deleted=False,
            moderation_status=1,
        ).count()
        if count >= need:
            return _grant_badge(user, SLUG_HELPFUL)
        return False

    @classmethod
    def on_answer_moderation_approved(cls, answer) -> bool:
        """Onaylı forum cevabı kaydı sonrası (tek cevap)."""
        user = answer.author
        if not user or not user.pk:
            return False
        return cls.try_helpful_badge_for_user(user)

    @classmethod
    def try_design_milestone_badge_for_user(cls, user: User) -> bool:
        """Tasarım sayısı yeterliyse Usta Paylaşımcı verir."""
        if not user or not user.pk:
            return False
        badge = Badge.objects.filter(slug=SLUG_MASTER_SHARER).first()
        need = badge.requirement_value if badge else 5
        from designs.models import Design

        count = Design.objects.filter(author=user).count()
        if count >= need:
            return _grant_badge(user, SLUG_MASTER_SHARER)
        return False

    @classmethod
    def on_design_created(cls, user: User) -> bool:
        """Yeni tasarım sonrası."""
        if not user or not user.pk:
            return False
        return cls.try_design_milestone_badge_for_user(user)

    @classmethod
    def check_popular_for_user(cls, user: Optional[User]) -> bool:
        """Kullanıcının herhangi bir soru / cevap / tasarımı eşik beğeniye ulaştı mı."""
        if not user or not user.pk:
            return False
        badge = Badge.objects.filter(slug=SLUG_POPULAR).first()
        thr = badge.requirement_value if badge else 50
        from questions.models import Question
        from answers.models import Answer
        from designs.models import Design

        if Question.objects.filter(author=user, is_deleted=False, like_count__gte=thr).exists():
            return _grant_badge(user, SLUG_POPULAR)
        if Answer.objects.filter(author=user, is_deleted=False, like_count__gte=thr).exists():
            return _grant_badge(user, SLUG_POPULAR)
        if Design.objects.filter(author=user, like_count__gte=thr).exists():
            return _grant_badge(user, SLUG_POPULAR)
        return False

    @classmethod
    def sync_all_behavior_badges(cls, user: User) -> list[str]:
        """
        Tüm davranış rozetlerini tek seferde değerlendirir (backfill / mevcut kullanıcılar).
        Yeni verilen rozetlerin slug listesini döner.
        """
        granted: list[str] = []
        if cls.on_profile_media_updated(user):
            granted.append(SLUG_WELCOME)
        if cls.try_helpful_badge_for_user(user):
            granted.append(SLUG_HELPFUL)
        if cls.try_design_milestone_badge_for_user(user):
            granted.append(SLUG_MASTER_SHARER)
        if cls.check_popular_for_user(user):
            granted.append(SLUG_POPULAR)
        return granted


def reputation_badges_gallery(user: User) -> list[dict]:
    """Profilde tüm rozetler + kazanıldı mı bilgisi."""
    earned = {
        ub.badge_id: ub
        for ub in UserBadge.objects.filter(user=user).select_related('badge')
    }
    out = []
    for b in Badge.objects.all().order_by('badge_type', 'id'):
        ub = earned.get(b.id)
        out.append(
            {
                'id': b.id,
                'slug': b.slug,
                'name': b.name,
                'description': b.description or '',
                'icon': b.icon or '',
                'icon_svg': b.icon_svg or '',
                'badge_type': b.badge_type,
                'requirement_value': b.requirement_value,
                'earned': ub is not None,
                'earned_at': ub.earned_at.isoformat() if ub else None,
            }
        )
    return out
