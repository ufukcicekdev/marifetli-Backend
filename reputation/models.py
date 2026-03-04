"""
Reputation System - Configurable points, history, badges
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


# İtibar kuralları (profilde gösterilen puan nasıl artar/azalır)
# Artış: soru paylaşma +5, cevap yazma +10, cevabın en iyi seçilmesi +25, gönderi/cevaba beğeni almak +2
# Azalış: spam cezası -20 (ileride rapor onaylanınca uygulanabilir), downvote -1 (ileride eklenebilir)
REPUTATION_RULES = {
    'question_posted': 5,       # Soru paylaştı
    'answer_posted': 10,        # Cevap yazdı
    'best_answer_selected': 25,  # Cevabı en iyi seçildi
    'like_received': 2,         # Gönderi veya cevabı beğenildi
    'spam_penalty': -20,        # Spam cezası (rapor onayı vb.)
    'downvote_received': -1,     # Olumsuz oy (ileride)
}


class ReputationHistory(models.Model):
    """Track all reputation changes"""
    REASON_CHOICES = [
        ('question_posted', 'Question Posted'),
        ('answer_posted', 'Answer Posted'),
        ('best_answer', 'Best Answer Selected'),
        ('like_received', 'Like Received'),
        ('spam_penalty', 'Spam Penalty'),
        ('downvote', 'Downvote Received'),
        ('admin_adjustment', 'Admin Adjustment'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reputation_history')
    points = models.IntegerField()  # Can be negative
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Reputation histories'

    def __str__(self):
        return f"{self.user.username}: {self.points} ({self.reason})"


class Badge(models.Model):
    """Milestone-based badges"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # Icon name or URL
    points_required = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    """User earned badges"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='users')
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')
