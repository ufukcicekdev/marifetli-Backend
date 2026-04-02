from django.contrib import admin
from django.utils import timezone
from .models import BlogPost, BlogComment, BlogLike, BlogTopicQueue


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'is_published', 'published_at', 'view_count', 'like_count', 'comment_count', 'created_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['view_count', 'like_count', 'comment_count', 'created_at', 'updated_at']
    date_hierarchy = 'published_at'

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'excerpt', 'featured_image', 'content', 'author', 'is_published', 'published_at'),
        }),
        ('İstatistikler', {
            'fields': ('view_count', 'like_count', 'comment_count', 'created_at', 'updated_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and obj.is_published and not obj.published_at:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username', 'post__title']
    raw_id_fields = ['post', 'author']

    def content_preview(self, obj):
        return (obj.content[:60] + '...') if len(obj.content) > 60 else obj.content
    content_preview.short_description = 'Yorum'


@admin.register(BlogLike)
class BlogLikeAdmin(admin.ModelAdmin):
    list_display = ['post', 'user', 'created_at']
    list_filter = ['created_at']
    raw_id_fields = ['post', 'user']


@admin.register(BlogTopicQueue)
class BlogTopicQueueAdmin(admin.ModelAdmin):
    list_display = [
        "topic",
        "is_completed",
        "generated_post",
        "completed_at",
        "created_at",
    ]
    list_filter = ["is_completed", "created_at", "completed_at"]
    search_fields = ["topic", "last_error", "generated_post__title"]
    raw_id_fields = ["generated_post"]
    readonly_fields = ["generated_post", "completed_at", "last_error", "created_at", "updated_at"]
