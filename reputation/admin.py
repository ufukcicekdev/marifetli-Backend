from django.contrib import admin

from .models import Badge, UserBadge, ReputationHistory


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "badge_type", "points_required", "requirement_value", "created_at")
    list_filter = ("badge_type",)
    search_fields = ("name", "slug", "description")


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "earned_at")
    list_filter = ("badge",)
    raw_id_fields = ("user", "badge")
    date_hierarchy = "earned_at"


@admin.register(ReputationHistory)
class ReputationHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "reason", "created_at")
    list_filter = ("reason",)
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"
