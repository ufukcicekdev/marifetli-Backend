from django.contrib import admin
from django.utils import timezone
from .models import BadWord, SuggestedBadWord, UserBan, AdminActionLog


@admin.register(BadWord)
class BadWordAdmin(admin.ModelAdmin):
    list_display = ["word", "is_active", "created_at"]
    list_editable = ["is_active"]
    list_filter = ["is_active"]
    search_fields = ["word"]


@admin.register(SuggestedBadWord)
class SuggestedBadWordAdmin(admin.ModelAdmin):
    list_display = ["word", "source", "status", "note", "created_at", "reviewed_at"]
    list_filter = ["status", "source"]
    search_fields = ["word"]
    list_editable = ["note"]
    actions = ["approve_selected", "reject_selected"]
    date_hierarchy = "created_at"

    @admin.action(description="Seçilenleri onayla (BadWord'e ekle)")
    def approve_selected(self, request, queryset):
        pending = queryset.filter(status="pending")
        n = 0
        for s in pending:
            BadWord.objects.get_or_create(word=s.word.strip().lower(), defaults={"is_active": True})
            s.status = "approved"
            s.reviewed_at = timezone.now()
            s.save(update_fields=["status", "reviewed_at"])
            n += 1
        self.message_user(request, f"{n} öneri BadWord listesine eklendi.")

    @admin.action(description="Seçilenleri reddet")
    def reject_selected(self, request, queryset):
        pending = queryset.filter(status="pending")
        now = timezone.now()
        updated = pending.update(status="rejected", reviewed_at=now)
        self.message_user(request, f"{updated} öneri reddedildi.")


@admin.register(UserBan)
class UserBanAdmin(admin.ModelAdmin):
    list_display = ["user", "reason", "banned_by", "banned_at", "banned_until", "is_active"]


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ["admin", "action", "target_type", "target_id", "created_at"]
    list_filter = ["action"]
