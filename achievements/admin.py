from django.contrib import admin
from .models import AchievementCategory, Achievement, UserAchievement, UserStreak


@admin.register(AchievementCategory)
class AchievementCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active']


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'order', 'target_count', 'is_active']
    list_filter = ['category', 'is_active']


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'unlocked_at']
    list_filter = ['achievement']


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'last_activity_date', 'current_streak_days', 'updated_at']
    search_fields = ['user__username']
