from django.db import models
from django.contrib.auth import get_user_model
from questions.models import Question

User = get_user_model()


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    content = models.TextField()
    is_best_answer = models.BooleanField(default=False)
    like_count = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Answer by {self.author.username} to {self.question.title}"

    class Meta:
        ordering = ['-created_at']


class AnswerLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answer_likes')
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'answer')

    def __str__(self):
        return f"{self.user.username} likes answer #{self.answer.id}"


class AnswerReport(models.Model):
    REPORT_CHOICES = [
        ('spam', 'Spam'),
        ('offensive', 'Offensive Content'),
        ('incorrect', 'Incorrect Information'),
        ('other', 'Other'),
    ]

    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_answers')
    reason = models.CharField(max_length=20, choices=REPORT_CHOICES)
    description = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_answer_reports')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report on answer #{self.answer.id} by {self.reporter.username}"

    class Meta:
        unique_together = ('answer', 'reporter')