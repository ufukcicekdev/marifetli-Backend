from django.db import models
from django.conf import settings


class EmailTemplate(models.Model):
    """Email template model for managing email templates"""
    
    TEMPLATE_CHOICES = [
        ('verification', 'Email Verification'),
        ('password_reset', 'Password Reset'),
        ('welcome', 'Welcome Email'),
        ('notification', 'General Notification'),
        ('answer_notification', 'Answer Notification'),
        ('comment_notification', 'Comment Notification'),
        ('follow_notification', 'Follow Notification'),
        ('kids_teacher_welcome', 'Marifetli Kids — Öğretmen hesabı (geçici şifre)'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_CHOICES, unique=True)
    subject = models.CharField(max_length=255, help_text='Email subject line')
    html_content = models.TextField(help_text='HTML content of the email')
    text_content = models.TextField(help_text='Plain text content of the email', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class SentEmail(models.Model):
    """Track all sent emails"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
    ]
    
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional data like user_id, token, etc.')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.recipient} - {self.subject}"
