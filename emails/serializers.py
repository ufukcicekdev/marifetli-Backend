from rest_framework import serializers
from .models import EmailTemplate, SentEmail


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serializer for EmailTemplate model"""
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'template_type', 'subject', 'html_content', 
            'text_content', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class SentEmailSerializer(serializers.ModelSerializer):
    """Serializer for SentEmail model"""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = SentEmail
        fields = [
            'id', 'recipient', 'subject', 'template', 'template_name',
            'status', 'sent_at', 'opened_at', 'clicked_at', 'error_message',
            'metadata', 'created_at'
        ]
        read_only_fields = ['created_at']
