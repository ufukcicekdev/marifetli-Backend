"""
Kullanıcı başına soru limiti ve “özellik açık mı?” yardımcıları.
"""
from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

from .models import CategoryExpertQuery

ISTANBUL = ZoneInfo("Europe/Istanbul")


def get_effective_category_expert_limit_period() -> str:
    """
    Env'de eski all_time kalmış olsa bile ürün beklentisi günlük limittir.
    Gerçek ömür boyu limit için CATEGORY_EXPERT_ALLOW_LIFETIME_EXPERT_LIMIT=True.
    """
    raw = (getattr(settings, "CATEGORY_EXPERT_LIMIT_PERIOD", "day") or "day").strip().lower()
    if raw not in ("day", "month", "all_time"):
        return "day"
    allow_lifetime = bool(getattr(settings, "CATEGORY_EXPERT_ALLOW_LIFETIME_EXPERT_LIMIT", False))
    if raw == "all_time" and not allow_lifetime:
        return "day"
    return raw


def category_expert_feature_enabled() -> bool:
    return bool(getattr(settings, "CATEGORY_EXPERT_ENABLED", False))


def _window_start_utc(period: str) -> datetime | None:
    """all_time için None; day/month için UTC eşiği."""
    if period not in ("day", "month"):
        return None
    local_now = timezone.now().astimezone(ISTANBUL)
    if period == "day":
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        local_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return local_start.astimezone(dt_timezone.utc)


def count_user_queries_in_period(user) -> int:
    period = get_effective_category_expert_limit_period()
    qs = CategoryExpertQuery.objects.filter(user=user)
    start = _window_start_utc(period)
    if start is not None:
        qs = qs.filter(created_at__gte=start)
    return qs.count()


def user_remaining_questions(user) -> tuple[int, int]:
    """(kalan, maksimum) — maksimum 0 ise limitsiz sayılır."""
    max_q = int(getattr(settings, "CATEGORY_EXPERT_MAX_QUESTIONS_PER_USER", 3) or 0)
    if max_q <= 0:
        return (999999, max_q)  # pratikte limitsiz
    used = count_user_queries_in_period(user)
    return (max(0, max_q - used), max_q)


def expert_backend_ready() -> bool:
    """Özellik açık + seçilen LLM sağlayıcı yapılandırılmış mı?"""
    if not category_expert_feature_enabled():
        return False
    from .providers import get_expert_llm_provider

    return get_expert_llm_provider().is_configured()
