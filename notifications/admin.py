from django.contrib import admin
from .models import Notification, NotificationSetting, FCMDeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'sender', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_notifications', 'push_notifications', 'notify_on_answer', 'notify_on_like', 'notify_on_follow']


@admin.register(FCMDeviceToken)
class FCMDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_name', 'created_at']
    search_fields = ['user__username', 'token']
