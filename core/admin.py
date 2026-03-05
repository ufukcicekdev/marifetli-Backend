from django.contrib import admin
from .models import SiteConfiguration, SocialMediaLink, ContactMessage


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'contact_email', 'contact_phone', 'updated_at']
    fieldsets = (
        ('Genel', {'fields': ('site_name', 'site_description')}),
        ('İletişim', {'fields': ('contact_email', 'contact_phone', 'contact_address', 'contact_description')}),
        ('Google Analytics & Search Console', {
            'fields': ('google_analytics_id', 'google_search_console_meta'),
            'description': 'Google Analytics (GA4) Ölçüm ID ve Search Console doğrulama meta değeri.',
        }),
        ('Bakım', {'fields': ('is_maintenance_mode', 'maintenance_message')}),
    )


@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(admin.ModelAdmin):
    list_display = ['platform', 'url', 'label', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['platform', 'is_active']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'name', 'email', 'read', 'answered', 'created_at']
    list_filter = ['read', 'answered', 'created_at']
    list_editable = ['read', 'answered']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['name', 'email', 'subject', 'message', 'created_at']
