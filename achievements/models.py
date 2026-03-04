"""
Başarılar (Achievements) - Reddit tarzı rozet sistemi.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AchievementCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name


class Achievement(models.Model):
    category = models.ForeignKey(AchievementCategory, on_delete=models.CASCADE, related_name='achievements')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    code = models.SlugField(max_length=80, unique=True)
    icon = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    target_count = models.PositiveIntegerField(null=True, blank=True, help_text='İlerleme başarıları için hedef sayı (örn. 10 yorum)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'order', 'id']

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='user_achievements')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"


class UserStreak(models.Model):
    """Kullanıcının günlük aktivite serisi (yorum, beğeni, gönderi = 1 gün sayılır)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='streak')
    last_activity_date = models.DateField(null=True, blank=True)
    current_streak_days = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kullanıcı serisi'
        verbose_name_plural = 'Kullanıcı serileri'

    def __str__(self):
        return f"{self.user.username}: {self.current_streak_days} gün"
