import base64
import mimetypes
import os
import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone
from .models import EmailTemplate, SentEmail
import logging

logger = logging.getLogger(__name__)


def _get_email_base_url():
    """E-posta içindeki mutlak URL'ler için base URL (logo artık base64 kullanıyor)."""
    base = getattr(settings, 'BACKEND_URL', None) or ''
    if base:
        return base.rstrip('/')
    hosts = getattr(settings, 'ALLOWED_HOSTS', []) or []
    for h in hosts:
        if h and str(h).strip() not in ('localhost', '127.0.0.1') and '.' in str(h):
            return 'https://' + str(h).strip()
    return ''


def _logo_to_data_uri(logo_field):
    """Logo dosyasını base64 data URI'ye çevirir; e-postada dış URL'ye ihtiyaç kalmaz."""
    if not logo_field:
        return None
    try:
        data = None
        path = getattr(logo_field, 'path', None)
        if path and os.path.exists(path):
            with open(path, 'rb') as f:
                data = f.read()
            name = path
        else:
            # Remote storage (S3 vb.): dosyayı açıp oku
            try:
                logo_field.open('rb')
                data = logo_field.read()
                name = getattr(logo_field, 'name', '') or ''
            finally:
                logo_field.close()
        if not data:
            return None
        b64 = base64.b64encode(data).decode('ascii')
        mime, _ = mimetypes.guess_type(name)
        mime = mime or 'image/png'
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.debug("Logo base64: %s", e)
        return None


def _get_email_base_context():
    """Site ayarlarından logo (base64 gömülü) ve site adını alır; e-posta şablonlarına verilir."""
    try:
        from core.models import SiteConfiguration
        config = SiteConfiguration.objects.first()
        if not config:
            return {'logo_url': None, 'logo_data_uri': None, 'site_name': 'Marifetli'}
        logo_data_uri = None
        logo_url = None
        if getattr(config, 'logo', None) and config.logo:
            logo_data_uri = _logo_to_data_uri(config.logo)
            if not logo_data_uri:
                raw_url = config.logo.url
                if raw_url and (raw_url.startswith('http://') or raw_url.startswith('https://')):
                    logo_url = raw_url
                else:
                    base = _get_email_base_url()
                    if base and raw_url:
                        logo_url = base + (raw_url if raw_url.startswith('/') else '/' + raw_url)
        return {
            'logo_url': logo_url,
            'logo_data_uri': logo_data_uri,
            'site_name': getattr(config, 'site_name', None) or 'Marifetli',
        }
    except Exception as e:
        logger.debug("Email base context (logo): %s", e)
        return {'logo_url': None, 'logo_data_uri': None, 'site_name': 'Marifetli'}


class EmailService:
    """Central email service for handling all email sending operations"""
    
    @staticmethod
    def send_email(recipient, subject, html_content, text_content='', from_email=None, metadata=None):
        """
        Send an email using SMTP2GO API and track it in the database
        
        Args:
            recipient: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
            from_email: Sender email (defaults to SMTP2GO_FROM_EMAIL)
            metadata: Additional data to store (dict)
        
        Returns:
            SentEmail object with status
        """
        from_email = from_email or getattr(settings, 'SMTP2GO_FROM_EMAIL', 'noreply@marifetli.com')
        
        # Create sent email record
        sent_email = SentEmail.objects.create(
            recipient=recipient,
            subject=subject,
            metadata=metadata or {}
        )
        
        try:
            api_key = (getattr(settings, 'SMTP2GO_API_KEY', None) or '').strip()

            if not api_key:
                # Yerel / SMTP-only kurulum: Django EMAIL_* ile gönder (SMTP2GO olmadan).
                try:
                    msg = EmailMultiAlternatives(
                        subject=subject,
                        body=text_content or '',
                        from_email=from_email,
                        to=[recipient],
                    )
                    if html_content:
                        msg.attach_alternative(html_content, 'text/html')
                    msg.send(fail_silently=False)
                    sent_email.status = 'sent'
                    sent_email.sent_at = django_timezone.now()
                    sent_email.save()
                    logger.info("Email sent via Django mail backend to %s", recipient)
                    return sent_email
                except Exception as django_exc:
                    logger.warning(
                        "SMTP2GO_API_KEY yok veya boş; Django e-postası da gönderilemedi: %s",
                        django_exc,
                    )
                    sent_email.status = 'failed'
                    sent_email.error_message = (
                        'Sağlayıcı (SMTP2GO) anahtarı yok; Django e-postası da başarısız: '
                        f'{django_exc}'
                    )
                    sent_email.save()
                    return sent_email

            # SMTP2GO expects api_key in header or payload, not HTTP Basic auth
            headers = {
                'Content-Type': 'application/json',
                'X-Smtp2go-Api-Key': api_key,
            }
            response = requests.post(
                'https://api.smtp2go.com/v3/email/send',
                headers=headers,
                json={
                    'api_key': api_key,
                    'sender': from_email,
                    'to': [recipient],
                    'subject': subject,
                    'html_body': html_content,
                    'text_body': text_content if text_content else '',
                },
                timeout=10
            )
            
            if response.status_code == 200:
                sent_email.status = 'sent'
                sent_email.sent_at = django_timezone.now()
                logger.info(f"Email sent successfully to {recipient}")
            else:
                sent_email.status = 'failed'
                sent_email.error_message = f"SMTP2GO API Error: {response.status_code} - {response.text}"
                logger.error(f"Failed to send email to {recipient}: {response.text}")
            
            sent_email.save()
            return sent_email
            
        except Exception as e:
            sent_email.status = 'failed'
            sent_email.error_message = str(e)
            sent_email.save()
            logger.error(f"Exception sending email to {recipient}: {str(e)}")
            return sent_email
    
    @staticmethod
    def send_template_email(recipient, template_type, context, from_email=None):
        """
        Send email using a stored template
        
        Args:
            recipient: Recipient email address
            template_type: Type of template (e.g., 'verification', 'password_reset')
            context: Context data for template rendering
            from_email: Sender email (optional)
        
        Returns:
            SentEmail object with status
        """
        try:
            template = EmailTemplate.objects.get(template_type=template_type, is_active=True)
        except EmailTemplate.DoesNotExist:
            logger.error(f"Email template '{template_type}' not found")
            return None

        # Tüm e-posta şablonlarında logo ve site adı kullanılabilsin
        base_ctx = _get_email_base_context()
        merged_context = {**base_ctx, **(context or {})}
        context = merged_context

        # Render template with context (template.html_content is e.g. 'emails/verification_email.html')
        subject = template.subject.format(**context) if context else template.subject
        html_content = render_to_string(template.html_content, context) if template.html_content else ''
        try:
            text_content = template.text_content.format(**context) if context and template.text_content else (template.text_content or '')
        except KeyError:
            text_content = template.text_content or ''
        
        # Metadata: only serializable values for JSONField (no model instances)
        metadata = {'template_type': template_type}
        if context:
            safe = (
                'token',
                'verification_url',
                'reset_url',
                'frontend_url',
                'username',
                'login_url',
                'reset_hint_url',
                'teacher_email',
            )
            for k in safe:
                if k in context and context[k] is not None:
                    metadata[k] = str(context[k]) if not isinstance(context[k], (str, int, float, bool)) else context[k]
        return EmailService.send_email(
            recipient=recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=from_email,
            metadata=metadata
        )
    
    @staticmethod
    def send_verification_email(user, token):
        """Send email verification email"""
        context = {
            'user': user,
            'token': token,
            'verification_url': f"{settings.FRONTEND_URL}/verify-email/{token}" if hasattr(settings, 'FRONTEND_URL') else f"/verify-email/{token}"
        }
        return EmailService.send_template_email(
            recipient=user.email,
            template_type='verification',
            context=context
        )
    
    @staticmethod
    def send_password_reset_email(user, token):
        """Send password reset email"""
        context = {
            'user': user,
            'token': token,
            'reset_url': f"{settings.FRONTEND_URL}/reset-password/{token}" if hasattr(settings, 'FRONTEND_URL') else f"/reset-password/{token}"
        }
        return EmailService.send_template_email(
            recipient=user.email,
            template_type='password_reset',
            context=context
        )

    @staticmethod
    def send_kids_password_reset_email(kids_user, token: str, reset_url: str):
        """Marifetli Kids (kids_users) şifre sıfırlama; şablonda user.username kullanılır."""

        class _KidsEmailUser:
            __slots__ = ("email", "username")

            def __init__(self, ku):
                self.email = ku.email
                name = (ku.first_name or "").strip()
                self.username = name or (
                    ku.email.split("@", 1)[0] if "@" in ku.email else ku.email
                )

        return EmailService.send_template_email(
            recipient=kids_user.email,
            template_type="password_reset",
            context={
                "user": _KidsEmailUser(kids_user),
                "token": token,
                "reset_url": reset_url,
            },
        )
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user"""
        context = {
            'user': user,
            'username': user.username,
            'frontend_url': getattr(settings, 'FRONTEND_URL', ''),
        }
        return EmailService.send_template_email(
            recipient=user.email,
            template_type='welcome',
            context=context
        )
    
    @staticmethod
    def send_kids_teacher_welcome_email(
        *,
        to_email: str,
        first_name: str,
        temp_password: str,
        login_url: str,
        reset_hint_url: str,
    ):
        """
        Kids yönetiminden oluşturulan öğretmene geçici şifre e-postası.
        `emails/kids_teacher_welcome_email.html` + DB şablonu `kids_teacher_welcome`; yoksa düz HTML fallback.
        """
        display_name = (first_name or "").strip() or "Öğretmen"
        context = {
            "display_name": display_name,
            "teacher_email": to_email,
            "temp_password": temp_password,
            "login_url": login_url,
            "reset_hint_url": reset_hint_url,
        }
        sent = EmailService.send_template_email(
            recipient=to_email,
            template_type="kids_teacher_welcome",
            context=context,
        )
        if sent is not None:
            return sent

        logger.warning(
            "Email template 'kids_teacher_welcome' bulunamadı; düz metin/HTML fallback kullanılıyor. "
            "Şablon için: python manage.py populate_email_templates"
        )
        subject = "Marifetli Kids — Öğretmen hesabınız hazır"
        html = (
            f"<p>Merhaba {display_name},</p>"
            "<p>Marifetli Kids öğretmen hesabınız oluşturuldu.</p>"
            f"<p><strong>Giriş e-postası:</strong> {to_email}<br/>"
            f"<strong>Geçici şifre:</strong> {temp_password}</p>"
            f"<p>Giriş: <a href=\"{login_url}\">{login_url}</a></p>"
            "<p>Güvenlik için ilk girişten sonra şifrenizi değiştirmenizi öneririz. "
            f"Giriş ekranındaki <em>Şifremi unuttum</em> akışı: "
            f"<a href=\"{reset_hint_url}\">{reset_hint_url}</a></p>"
        )
        text = (
            f"Merhaba {display_name},\n\n"
            "Marifetli Kids öğretmen hesabınız oluşturuldu.\n"
            f"Giriş e-postası: {to_email}\n"
            f"Geçici şifre: {temp_password}\n\n"
            f"Giriş: {login_url}\n\n"
            "İlk girişten sonra şifrenizi değiştirmeniz önerilir.\n"
        )
        return EmailService.send_email(
            recipient=to_email,
            subject=subject,
            html_content=html,
            text_content=text,
            metadata={"kids_teacher_welcome": True, "template_fallback": True},
        )

    @staticmethod
    def send_notification_email(user, subject, message, notification_type='general'):
        """Send general notification email"""
        context = {
            'user': user,
            'message': message,
            'notification_type': notification_type,
            'frontend_url': getattr(settings, 'FRONTEND_URL', ''),
        }
        return EmailService.send_template_email(
            recipient=user.email,
            template_type='notification',
            context=context
        )