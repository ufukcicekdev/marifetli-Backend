"""Sorgu optimizasyonu: kullanıcı rozetleri (avatar köşesi için)."""

from django.db.models import Prefetch

from .models import UserBadge


def author_badges_prefetch():
    """Question.author / Answer.author için UserBadge prefetch (yeniden eskiye)."""
    return Prefetch(
        'author__badges',
        queryset=UserBadge.objects.select_related('badge').order_by('-earned_at'),
    )
