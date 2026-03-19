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
    if notification_type == 'comment_design' and not _should_send(recipient, 'notify_on_answer'):
        return False
    if notification_type in ('like_question', 'like_answer', 'like_design') and not _should_send(recipient, 'notify_on_like'):
        return False
    if notification_type == 'follow' and not _should_send(recipient, 'notify_on_follow'):
        return False
    if notification_type == 'mention' and not _should_send(recipient, 'notify_mention'):
        return False
    return True


def _should_send_email(recipient, notification_type: str) -> bool:
    """E-posta gönderilsin mi? (email_notifications + türe özel ayar)"""
    if not _should_send(recipient, 'email_notifications'):
        return False
    if notification_type == 'answer' and not _should_send(recipient, 'notify_on_answer'):
        return False
    if notification_type == 'comment_design' and not _should_send(recipient, 'notify_on_answer'):
        return False
    if notification_type in ('like_question', 'like_answer', 'like_design') and not _should_send(recipient, 'notify_on_like'):
        return False
    if notification_type == 'follow' and not _should_send(recipient, 'notify_on_follow'):
        return False
    if notification_type == 'mention' and not _should_send(recipient, 'notify_mention'):
        return False
    return True


def create_notification(recipient, sender, notification_type: str, message: str, *, question=None, answer=None, design=None, community=None):
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
        design=design,
        community=community,
    )
    # E-posta (ayarlara göre)
    if _should_send_email(recipient, notification_type):
        try:
            from emails.services import EmailService
            EmailService.send_notification_email(recipient, f"Bildirim: {message[:50]}", message, notification_type)
        except Exception:
            pass
    # Push (FCM) - ayarlara göre (push_notifications + notify_on_answer vb.)
    if _should_send_push(recipient, notification_type):
        send_fcm_to_user(
            recipient,
            "Marifetli",
            message,
            notification_type,
            question=question,
            answer=answer,
            design=design,
            sender=sender,
        )
    return notif


def _build_notification_url(notification_type: str, question=None, answer=None, design=None, sender=None):
    """Push tıklanınca açılacak sayfa URL'i (path only)."""
    base = (getattr(settings, 'FRONTEND_URL', None) or '').rstrip('/')
    path = '/'
    if question and getattr(question, 'slug', None):
        path = f'/soru/{question.slug}'
        if answer and getattr(answer, 'pk', None):
            path = f'{path}#comment-{answer.pk}'
    elif design and getattr(design, 'pk', None):
        path = f'/tasarim/{design.pk}'
    elif sender and getattr(sender, 'username', None):
        path = f'/profil/{sender.username}'
    elif notification_type == 'community_join_request' and getattr(settings, 'FRONTEND_URL', None):
        # community slug data'da eklenebilir; genel bildirimler sayfası
        path = '/bildirimler'
    return f"{base}{path}" if base else path


def _notification_icon_type(notification_type: str) -> str:
    """Bildirim türüne göre SW'da kullanılacak ikon anahtarı (beğeni/ yorum/ takip vb.)."""
    if notification_type in ('like_question', 'like_answer'):
        return 'like'
    if notification_type == 'like_design':
        return 'like'
    if notification_type == 'answer':
        return 'comment'
    if notification_type == 'comment_design':
        return 'comment'
    if notification_type == 'follow':
        return 'follow'
    if notification_type == 'mention':
        return 'mention'
    if notification_type == 'community_join_request':
        return 'community'
    return 'default'


def _sender_image_url(sender) -> str | None:
    """Gönderenin profil resmi için tam URL (FCM image alanı için). S3 kullanıyorsan .url zaten tam döner."""
    if not sender or not getattr(sender, 'profile_picture', None) or not sender.profile_picture:
        return None
    url = getattr(sender.profile_picture, 'url', None) or ''
    return url if url.startswith('http') else None


def send_fcm_to_user(user, title: str, body: str, notification_type: str = '', question=None, answer=None, design=None, sender=None):
    """
    Kullanıcının kayıtlı cihazlarına FCM push gönderir.
    Firebase config (FCM credentials) .env'den veya settings'ten okunur.
    """
    tokens = list(FCMDeviceToken.objects.filter(user=user).values_list('token', flat=True))
    if not tokens:
        logger.debug("FCM: user %s has no registered tokens, skip push", user.username)
        return
    data = {'type': notification_type, 'icon_type': _notification_icon_type(notification_type)}
    if question_id := (question.pk if question else None):
        data['question_id'] = str(question_id)
    if question and getattr(question, 'slug', None):
        data['question_slug'] = str(question.slug)
    if answer_id := (answer.pk if answer else None):
        data['answer_id'] = str(answer_id)
    if design_id := (design.pk if design else None):
        data['design_id'] = str(design_id)
    data['url'] = _build_notification_url(notification_type, question=question, answer=answer, design=design, sender=sender)
    image_url = _sender_image_url(sender)
    _send_fcm(tokens, title=title, body=body, data=data, image_url=image_url)


def _send_fcm(tokens: list, title: str, body: str, data: dict = None, image_url: str = None):
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
    notification_kw = {'title': title, 'body': body}
    if image_url:
        notification_kw['image'] = image_url
    notification = messaging.Notification(**notification_kw)
    # firebase-admin 7+ send_multicast kaldırıldı; tek tek send() ile gönderiyoruz (tüm sürümlerde çalışır)
    for token in tokens:
        try:
            msg = messaging.Message(notification=notification, data=data_flat or {}, token=token)
            messaging.send(msg)
        except Exception as e:
            err_msg = (getattr(e, 'message', None) or str(e)) or ''
            err_lower = err_msg.lower()
            logger.warning("FCM: token gönderilemedi: %s", err_msg)
            # Geçersiz token'ları veritabanından kaldır: eski cihaz, farklı proje (SenderId mismatch) vb.
            is_invalid = (
                'notregistered' in err_lower
                or 'requested entity was not found' in err_lower
                or 'senderid mismatch' in err_lower
                or 'mismatched-credential' in err_lower
            )
            if is_invalid:
                deleted, _ = FCMDeviceToken.objects.filter(token=token).delete()
                if deleted:
                    logger.info("FCM: geçersiz token silindi (cihaz kaldırıldı veya farklı proje ile alınmış olabilir)")
