from django.contrib import admin
from .models import SiteConfiguration, SocialMediaLink, ContactMessage


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'contact_email', 'contact_phone', 'updated_at']
    fieldsets = (
        ('Genel', {'fields': ('site_name', 'site_description')}),
        ('Logo & Favicon', {
            'fields': ('logo', 'favicon'),
            'description': 'Site logosu (header) ve tarayıcı sekmesi ikonu (favicon).',
        }),
        ('Hakkımızda', {
            'fields': ('about_summary', 'about_content'),
            'description': 'about_summary: Anasayfa sidebar ve önizlemede gösterilir. about_content: /hakkimizda sayfasının tam metni.',
        }),
        ('İletişim', {'fields': ('contact_email', 'contact_phone', 'contact_address', 'contact_description')}),
        ('Google Analytics & Search Console', {
            'fields': ('google_analytics_id', 'google_search_console_meta'),
            'description': 'Google Analytics (GA4) Ölçüm ID ve Search Console doğrulama meta değeri.',
        }),
        ('Tema', {
            'fields': ('primary_color',),
            'description': (
                'Vurgu rengi (hex, örn: #e85d04). Boş bırakılırsa varsayılan canlı turuncu kullanılır. '
                'Örnekler: #e85d04 Turuncu, #0d9488 Teal, #2563eb Mavi, #dc2626 Kırmızı, #16a34a Yeşil, #9333ea Mor, #d97706 Amber.'
            ),
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
