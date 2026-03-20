"""
Kullanıcı rütbesi (seviye başlığı) — kaynak: UserProfile.reputation (itibar puanı).
"""
from __future__ import annotations

from django.contrib.auth import get_user_model

User = get_user_model()


def title_for_reputation_points(points: int) -> str:
    """0–100 Yeni Zanaatkar, 101–500 Maharetli Çırak, 501–1500 Gözü Pek Kalfa, 1501+ Baş Usta."""
    p = max(0, int(points or 0))
    if p <= 100:
        return 'Yeni Zanaatkar'
    if p <= 500:
        return 'Maharetli Çırak'
    if p <= 1500:
        return 'Gözü Pek Kalfa'
    return 'Baş Usta'


def display_level_title_for_user(user: User) -> str:
    """Serializer / API için: DB alanı doluysa onu, değilse itibardan hesaplananı döner."""
    raw = (getattr(user, 'current_level_title', None) or '').strip()
    if raw:
        return raw
    from users.models import UserProfile

    try:
        rep = user.profile.reputation
    except UserProfile.DoesNotExist:
        rep = 0
    return title_for_reputation_points(rep)


def sync_user_level_title(user: User, *, save: bool = True) -> str:
    """Profil itibarına göre User.current_level_title günceller."""
    from users.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'reputation': 0})
    title = title_for_reputation_points(profile.reputation)
    if getattr(user, 'current_level_title', None) != title:
        user.current_level_title = title
        if save:
            user.save(update_fields=['current_level_title', 'updated_at'])
    return title
