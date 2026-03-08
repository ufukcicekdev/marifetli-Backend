from django.contrib import admin
from .models import Community, CommunityMember


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category', 'owner', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ('owner', 'category')


@admin.register(CommunityMember)
class CommunityMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'created_at')
    list_filter = ('community',)
    raw_id_fields = ('user', 'community')
