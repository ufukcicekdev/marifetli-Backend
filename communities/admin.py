from django.contrib import admin
from .models import Community, CommunityMember, CommunityBan, CommunityJoinRequest, CommunityDeletionLog


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category', 'owner', 'join_type', 'created_at')
    list_filter = ('category', 'join_type', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ('owner', 'category')


@admin.register(CommunityMember)
class CommunityMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'role', 'created_at')
    list_filter = ('community', 'role')
    raw_id_fields = ('user', 'community')


@admin.register(CommunityBan)
class CommunityBanAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'banned_by', 'created_at')
    list_filter = ('community',)
    raw_id_fields = ('user', 'community', 'banned_by')


@admin.register(CommunityJoinRequest)
class CommunityJoinRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'status', 'reviewed_by', 'created_at')
    list_filter = ('community', 'status')
    raw_id_fields = ('user', 'community', 'reviewed_by')


@admin.register(CommunityDeletionLog)
class CommunityDeletionLogAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'owner_username', 'deleted_by', 'member_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'slug', 'reason', 'owner_username')
    readonly_fields = ('slug', 'name', 'category_name', 'owner_username', 'owner_id', 'deleted_by', 'reason', 'member_count', 'created_at')
    raw_id_fields = ('deleted_by',)
