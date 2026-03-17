from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Follow, UserNotificationPreference, LoginHistory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "is_bot", "is_staff", "is_active", "date_joined")
    list_filter = ("is_bot", "is_staff", "is_active", "gender")
    search_fields = ("username", "email", "first_name")
    ordering = ("-date_joined",)
    filter_horizontal = ()
    fieldsets = BaseUserAdmin.fieldsets + (("Ek", {"fields": ("bio", "gender", "is_bot", "profile_picture", "cover_image")}),)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "reputation", "is_private")
    search_fields = ("user__username",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email_notifications", "push_notifications")


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "success", "created_at")
    list_filter = ("success",)
    readonly_fields = ("created_at",)
