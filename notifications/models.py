from django.db import models
from django.contrib.auth import get_user_model
from questions.models import Question
from answers.models import Answer

User = get_user_model()


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('answer', 'Question Answered'),
        ('like_question', 'Question Liked'),
        ('like_answer', 'Answer Liked'),
        ('follow', 'User Followed'),
        ('mention', 'User Mentioned'),
        ('best_answer', 'Best Answer Selected'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.notification_type}"

    class Meta:
        ordering = ['-created_at']


class NotificationSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_setting')
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    desktop_notifications = models.BooleanField(default=True)
    notify_on_answer = models.BooleanField(default=True)
    notify_on_like = models.BooleanField(default=True)
    notify_on_follow = models.BooleanField(default=True)
    notify_mention = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification settings for {self.user.username}"