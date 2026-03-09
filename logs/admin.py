from django.contrib import admin
from django.utils.html import format_html
from .models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at", "level_badge", "logger_name", "message_short", "source"]
    list_filter = ["level", "source", "logger_name"]
    search_fields = ["message", "logger_name", "source"]
    readonly_fields = ["created_at", "level", "logger_name", "message", "source", "extra"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_per_page = 50

    def level_badge(self, obj):
        colors = {
            "DEBUG": "gray",
            "INFO": "green",
            "WARNING": "orange",
            "ERROR": "red",
            "CRITICAL": "darkred",
        }
        color = colors.get(obj.level, "gray")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color,
            obj.level,
        )

    level_badge.short_description = "Seviye"

    def message_short(self, obj):
        return (obj.message[:80] + "…") if len(obj.message) > 80 else obj.message

    message_short.short_description = "Mesaj"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
