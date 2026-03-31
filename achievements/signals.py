"""
Başarı ödülü için sinyaller - ilgili eylemlerde başarı kontrolü yapılır.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from users.models import User
from questions.models import Question
from answers.models import Answer

from . import services

User = get_user_model()


@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        services.check_and_award_on_signup(instance)


@receiver(post_save, sender=Question)
def on_question_created(sender, instance, created, **kwargs):
    if created and instance.status == 'open':
        user = instance.author
        services.check_and_award_on_first_question(user)
        count = Question.objects.filter(author=user, status='open').count()
        services.check_and_award_on_question_count(user, count)
        services.record_activity_and_check_streak(user)
        from reputation.services import award_reputation
        award_reputation(user, 'question_posted', content_object=instance, description='Soru paylaştın')
        # Takip edenlere bildirim: "X yeni gönderi paylaştı"
        from users.models import Follow
        from notifications.services import create_notification
        from core.i18n_catalog import translate
        from core.i18n_resolve import language_from_user

        follower_ids = Follow.objects.filter(following=user).values_list('follower_id', flat=True)
        from users.models import User as U
        for fid in follower_ids:
            if fid != user.pk:
                try:
                    recipient = U.objects.get(pk=fid)
                    _lang = language_from_user(recipient)
                    create_notification(
                        recipient, user, 'followed_post',
                        translate(
                            _lang,
                            'main.notif.followed_post',
                            username=user.username,
                            title=instance.title[:50],
                        ),
                        question=instance,
                    )
                except Exception:
                    pass


@receiver(post_save, sender=Answer)
def on_answer_created(sender, instance, created, **kwargs):
    if created:
        user = instance.author
        # Farklı sorulardaki cevap sayısı (aynı soruya birden fazla cevap tek sayılır)
        count = Answer.objects.filter(author=user).values('question').distinct().count()
        services.check_and_award_on_answer_count(user, count)
        services.record_activity_and_check_streak(user)
        from reputation.services import award_reputation
        award_reputation(user, 'answer_posted', content_object=instance, description='Cevap yazdın')
        # Soru sahibine bildirim moderasyondan geçip yayınlandıktan sonra gönderilir (cronjobs.tasks answer on_approved)


def connect_signals():
    """App ready'de çağrılır - signals'ları bağla"""
    pass  # @receiver decorator zaten bağlıyor
