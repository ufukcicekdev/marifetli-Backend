"""
Bildirim oluşturma ve (opsiyonel) e-posta / push gönderme.
"""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Notification, NotificationSetting, FCMDeviceToken

User = get_user_model()
logger = logging.getLogger(__name__)


class FCMService:
    """Firebase Cloud Messaging ile push bildirim gönderimi."""

    _initialized = False

    @classmethod
    def initialize(cls):
        """Firebase Admin SDK'yı .env'deki credentials ile başlatır."""
        if cls._initialized:
            return
        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError as e:
            logger.warning("FCM: firebase_admin yüklü değil: %s", e)
            return
        if firebase_admin._apps:
            cls._initialized = True
            return
        project_id = getattr(settings, 'FIREBASE_PROJECT_ID', None) or ''
        private_key = getattr(settings, 'FIREBASE_PRIVATE_KEY', None) or ''
        client_email = getattr(settings, 'FIREBASE_CLIENT_EMAIL', None) or ''
        print("project_id", project_id)
        print("private_key", private_key)
        print("client_email", client_email)
        if not (project_id and private_key and client_email):
            logger.warning("Firebase credentials not found in settings. Push notifications disabled.")
            return
        try:
            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key.replace('\\n', '\n'),  # Fix escaped newlines
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            cls._initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error("Error initializing Firebase Admin SDK: %s", e)


def _should_send(recipient, setting_key: str) -> bool:
    """Kullanıcı bu tür bildirimleri almak istiyor mu?"""
    try:
        s = NotificationSetting.objects.get(user=recipient)
        return getattr(s, setting_key, True)
    except NotificationSetting.DoesNotExist:
        return True


def _should_send_push(recipient, notification_type: str) -> bool:
    """Push gönderilsin mi? (push_notifications + türe özel ayar)"""
    if not _should_send(recipient, 'push_notifications'):
        return False
    if notification_type == 'answer' and not _should_send(recipient, 'notify_on_answer'):
        return False
    if notification_type in ('like_question', 'like_answer') and not _should_send(recipient, 'notify_on_like'):
        return False
    if notification_type == 'follow' and not _should_send(recipient, 'notify_on_follow'):
        return False
    if notification_type == 'mention' and not _should_send(recipient, 'notify_mention'):
        return False
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
    # Push (FCM) - ayarlara göre (push_notifications + notify_on_answer vb.)
    if _should_send_push(recipient, notification_type):
        send_fcm_to_user(recipient, "Marifetli", message, notification_type, question=question, answer=answer, sender=sender)
    return notif


def _build_notification_url(notification_type: str, question=None, answer=None, sender=None):
    """Push tıklanınca açılacak sayfa URL'i (path only)."""
    base = (getattr(settings, 'FRONTEND_URL', None) or '').rstrip('/')
    path = '/'
    if question and getattr(question, 'slug', None):
        path = f'/soru/{question.slug}'
        if answer and getattr(answer, 'pk', None):
            path = f'{path}#comment-{answer.pk}'
    elif sender and getattr(sender, 'username', None):
        path = f'/profil/{sender.username}'
    elif notification_type == 'community_join_request' and getattr(settings, 'FRONTEND_URL', None):
        # community slug data'da eklenebilir; genel bildirimler sayfası
        path = '/bildirimler'
    return f"{base}{path}" if base else path


def send_fcm_to_user(user, title: str, body: str, notification_type: str = '', question=None, answer=None, sender=None):
    """
    Kullanıcının kayıtlı cihazlarına FCM push gönderir.
    Firebase config (FCM credentials) .env'den veya settings'ten okunur.
    """
    tokens = list(FCMDeviceToken.objects.filter(user=user).values_list('token', flat=True))
    if not tokens:
        logger.debug("FCM: user %s has no registered tokens, skip push", user.username)
        return
    data = {'type': notification_type}
    if question_id := (question.pk if question else None):
        data['question_id'] = str(question_id)
    if question and getattr(question, 'slug', None):
        data['question_slug'] = str(question.slug)
    if answer_id := (answer.pk if answer else None):
        data['answer_id'] = str(answer_id)
    data['url'] = _build_notification_url(notification_type, question=question, answer=answer, sender=sender)
    _send_fcm(tokens, title=title, body=body, data=data)


def _send_fcm(tokens: list, title: str, body: str, data: dict = None):
    """Firebase Cloud Messaging ile push gönder. FCMService.initialize() kullanır."""
    if not tokens:
        return
    FCMService.initialize()
    if not FCMService._initialized:
        return
    try:
        from firebase_admin import messaging
    except ImportError:
        return
    data_flat = {k: str(v) for k, v in (data or {}).items()}
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data_flat,
        tokens=tokens,
    )
    try:
        response = messaging.send_multicast(message)
        if response.failure_count > 0:
            for i, send_response in enumerate(response.responses):
                if not send_response.success:
                    logger.warning(
                        "FCM: token[%s] gönderilemedi: %s",
                        i,
                        getattr(send_response.exception, 'message', send_response.exception),
                    )
    except Exception as e:
        logger.exception("FCM: send_multicast hatası: %s", e)
