"""
Bot aktivite — Admin'de uygulama görünsün diye BotYonetimi kayıtlı.
Liste sayfasına girildiğinde doğrudan yönetim paneline (/admin/bot-activity/) yönlendirilir.
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import BotYonetimi


@admin.register(BotYonetimi)
class BotYonetimiAdmin(admin.ModelAdmin):
    list_display = ("__str__",)
    list_display_links = None

    def changelist_view(self, request, extra_context=None):
        """Liste sayfasına girildiğinde bot yönetim paneline yönlendir."""
        return redirect("/admin/bot-activity/")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False
