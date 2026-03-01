"""
Hot score algorithm for trending questions
"""
from django.utils import timezone
from django.db.models import F


def calculate_hot_score(question):
    """
    Hot score = (views * 0.1) + (answers * 2) + (likes * 3) + recency_decay
    recency_decay = 10 / (1 + hours_since_posted * 0.1)
    """
    hours = (timezone.now() - question.created_at).total_seconds() / 3600
    recency = 10 / (1 + hours * 0.1)
    return (
        question.view_count * 0.1 +
        question.answer_count * 2 +
        question.like_count * 3 +
        recency
    )


def update_question_hot_score(question):
    """Update and save hot score for a question"""
    question.hot_score = calculate_hot_score(question)
    question.save(update_fields=['hot_score'])


def recalculate_all_hot_scores():
    """Batch update hot scores for all questions"""
    from .models import Question
    for q in Question.objects.filter(is_deleted=False).iterator():
        q.hot_score = calculate_hot_score(q)
        Question.objects.filter(pk=q.pk).update(hot_score=q.hot_score)
