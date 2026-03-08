"""
Moderation System - User ban, shadow ban, admin logs, bad word list, LLM moderation
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BadWord(models.Model):
    """Kötü kelime listesi - yorum/soru metninde eşleşirse kullanıcı uyarılır."""
    word = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .services import invalidate_bad_word_cache
        invalidate_bad_word_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        from .services import invalidate_bad_word_cache
        invalidate_bad_word_cache()

    class Meta:
        ordering = ['word']
        verbose_name = 'Kötü kelime'
        verbose_name_plural = 'Kötü kelimeler'

    def __str__(self):
        return self.word


class SuggestedBadWord(models.Model):
    """
    LLM'den dönen önerilen kötü kelimeler. Doğrudan BadWord'e eklenmez;
    admin onayı ile Onayla -> BadWord'e eklenir, Reddet -> reddedilir.
    (Örn. "makrome" el işi adı olarak dönmüş olabilir, küfür değildir.)
    """
    STATUS_CHOICES = [
        ("pending", "Beklemede"),
        ("approved", "Onaylandı (BadWord'e eklendi)"),
        ("rejected", "Reddedildi"),
    ]
    word = models.CharField(max_length=100)
    source = models.CharField(max_length=50, default="llm")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Önerilen kötü kelime"
        verbose_name_plural = "Önerilen kötü kelimeler"

    def __str__(self):
        return f"{self.word} ({self.get_status_display()})"


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
