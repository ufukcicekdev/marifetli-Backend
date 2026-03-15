from django.contrib import admin
from .models import Design


@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "license", "add_watermark", "created_at")
    list_filter = ("license", "add_watermark")
    search_fields = ("author__username", "tags")
    readonly_fields = ("created_at",)
