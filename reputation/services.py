"""
Reputation service - award points and check badges
"""
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import ReputationHistory, Badge, UserBadge, REPUTATION_RULES
from .leveling import sync_user_level_title

User = get_user_model()


def award_reputation(user: User, reason: str, points: int = None, content_object=None, description: str = ''):
    """Award reputation points and update user profile"""
    if points is None:
        points = REPUTATION_RULES.get(reason, 0)

    from users.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'reputation': 0})
    profile.reputation = max(0, profile.reputation + points)
    profile.save(update_fields=['reputation', 'updated_at'])

    content_type = ContentType.objects.get_for_model(content_object) if content_object else None
    object_id = content_object.pk if content_object else None

    ReputationHistory.objects.create(
        user=user,
        points=points,
        reason=reason,
        description=description,
        content_type=content_type,
        object_id=object_id,
    )

    check_and_award_badges(user)
    # Başarılar (achievements) itibar eşiklerini kontrol et (100, 1000 vb.)
    from achievements.services import check_and_award_on_reputation
    check_and_award_on_reputation(user, profile.reputation)
    sync_user_level_title(user)


def check_and_award_badges(user: User):
    """İtibar eşiği olan (milestone) rozetleri verir; davranış rozetleri BadgeService ile."""
    from users.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'reputation': 0})
    earned = set(UserBadge.objects.filter(user=user).values_list('badge_id', flat=True))
    for badge in (
        Badge.objects.filter(
            badge_type=Badge.BadgeType.MILESTONE,
            points_required__lte=profile.reputation,
        )
        .exclude(id__in=earned)
        .order_by('points_required', 'id')
    ):
        UserBadge.objects.create(user=user, badge=badge)
