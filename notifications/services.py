"""
Bildirim oluşturma ve (opsiyonel) e-posta / push gönderme.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Notification, NotificationSetting, FCMDeviceToken

User = get_user_model()


def _should_send(recipient, setting_key: str) -> bool:
    """Kullanıcı bu tür bildirimleri almak istiyor mu?"""
    try:
        s = NotificationSetting.objects.get(user=recipient)
        return getattr(s, setting_key, True)
    except NotificationSetting.DoesNotExist:
        return True


def create_notification(recipient, sender, notification_type: str, message: str, *, question=None, answer=None, community=None):
    """
    Bir bildirim kaydı oluşturur. İsteğe bağlı e-posta ve push gönderir.
    recipient: User; sender: User veya None (sistem bildirimi, örn. moderasyon).
    """
    if sender is not None and recipient.pk == sender.pk:
        return None
    notif = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        message=message,
        question=question,
        answer=answer,
        community=community,
    )
    # E-posta (ayarlara göre)
    if _should_send(recipient, 'email_notifications'):
        try:
            from emails.services import EmailService
            EmailService.send_notification_email(recipient, f"Bildirim: {message[:50]}", message, notification_type)
        except Exception:
            pass
    # Push (FCM) - ayarlara göre
    if _should_send(recipient, 'push_notifications'):
        send_fcm_to_user(recipient, "Marifetli", message, notification_type, question=question, answer=answer)
    return notif


def send_fcm_to_user(user, title: str, body: str, notification_type: str = '', question=None, answer=None):
    """
    Kullanıcının kayıtlı cihazlarına FCM push gönderir.
    Firebase config (FCM credentials) .env'den veya settings'ten okunur.
    """
    tokens = list(FCMDeviceToken.objects.filter(user=user).values_list('token', flat=True))
    if not tokens:
        return
    data = {'type': notification_type}
    if question_id := (question.pk if question else None):
        data['question_id'] = str(question_id)
    if question and getattr(question, 'slug', None):
        data['question_slug'] = str(question.slug)
    if answer_id := (answer.pk if answer else None):
        data['answer_id'] = str(answer_id)
    _send_fcm(tokens, title=title, body=body, data=data)


def _send_fcm(tokens: list, title: str, body: str, data: dict = None):
    """Firebase Cloud Messaging ile push gönder. Config yoksa sessizce çıkar."""
    if not tokens:
        return
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except ImportError:
        return
    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None) or ''
    if not cred_path:
        return
    if not firebase_admin._apps:
        try:
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
        except Exception:
            return
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
    )
    try:
        messaging.send_multicast(message)
    except Exception:
        pass
