"""
Moderation System - User ban, shadow ban, admin logs
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UserBan(models.Model):
    """User ban record"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ban_record')
    reason = models.TextField()
    banned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bans_issued')
    banned_at = models.DateTimeField(auto_now_add=True)
    banned_until = models.DateTimeField(null=True, blank=True)  # None = permanent
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Ban: {self.user.username}"


class AdminActionLog(models.Model):
    """Log admin actions for audit"""
    ACTION_CHOICES = [
        ('ban_user', 'Ban User'),
        ('unban_user', 'Unban User'),
        ('delete_content', 'Delete Content'),
        ('resolve_report', 'Resolve Report'),
        ('shadow_ban', 'Shadow Ban'),
    ]

    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='admin_actions')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50, blank=True)  # 'user', 'question', etc.
    target_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
