from django.contrib import admin
from .models import Design, DesignImage, DesignLike, DesignComment


class DesignImageInline(admin.TabularInline):
    model = DesignImage
    extra = 0


@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "license", "like_count", "comment_count", "add_watermark", "created_at")
    list_filter = ("license", "add_watermark")
    search_fields = ("author__username", "tags")
    readonly_fields = ("created_at",)
    inlines = [DesignImageInline]


@admin.register(DesignLike)
class DesignLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "design", "created_at")
    search_fields = ("user__username", "design__id")
    readonly_fields = ("created_at",)


@admin.register(DesignComment)
class DesignCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "design", "created_at")
    search_fields = ("author__username", "design__id", "content")
    readonly_fields = ("created_at", "updated_at")
