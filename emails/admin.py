from django.contrib import admin
from .models import EmailTemplate, SentEmail


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'subject', 'is_active', 'created_at', 'updated_at']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'subject', 'html_content']
    ordering = ['name']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type', 'subject')
        }),
        ('Content', {
            'fields': ('html_content', 'text_content'),
            'classes': ('wide',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'template_name', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'template', 'created_at']
    search_fields = ['recipient', 'subject']
    readonly_fields = ['recipient', 'subject', 'template', 'status', 'sent_at', 'opened_at', 'clicked_at', 'error_message', 'metadata', 'created_at']
    ordering = ['-created_at']
    
    def template_name(self, obj):
        return obj.template.name if obj.template else '-'
    template_name.short_description = 'Template'
