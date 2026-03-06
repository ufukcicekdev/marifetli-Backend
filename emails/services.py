import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .models import EmailTemplate, SentEmail
import logging

logger = logging.getLogger(__name__)


def _get_email_base_url():
    """E-posta içindeki mutlak URL'ler (logo vb.) için base URL. BACKEND_URL yoksa ALLOWED_HOSTS'tan türetir."""
    base = getattr(settings, 'BACKEND_URL', None) or ''
    if base:
        return base.rstrip('/')
    hosts = getattr(settings, 'ALLOWED_HOSTS', []) or []
    for h in hosts:
        if h and str(h).strip() not in ('localhost', '127.0.0.1') and '.' in str(h):
            return 'https://' + str(h).strip()
    return ''


def _get_email_base_context():
    """Site ayarlarından logo ve site adını alır; e-posta şablonlarına verilir."""
    try:
        from core.models import SiteConfiguration
        config = SiteConfiguration.objects.first()
        if not config:
            return {'logo_url': None, 'site_name': 'Marifetli'}
        logo_url = None
        if getattr(config, 'logo', None) and config.logo:
            base = _get_email_base_url()
            if base:
                # config.logo.url zaten / ile başlar (örn. /media/site/logo.png)
                logo_url = base + config.logo.url
        return {
            'logo_url': logo_url,
            'site_name': getattr(config, 'site_name', None) or 'Marifetli',
        }
    except Exception as e:
        logger.debug("Email base context (logo): %s", e)
        return {'logo_url': None, 'site_name': 'Marifetli'}


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
            # Using SMTP2GO API
            api_key = getattr(settings, 'SMTP2GO_API_KEY', None)
            
            if not api_key:
                logger.warning("SMTP2GO_API_KEY not configured. Email not sent.")
                sent_email.status = 'failed'
                sent_email.error_message = 'SMTP2GO_API_KEY not configured'
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
                sent_email.sent_at = sent_email.created_at
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
            safe = ('token', 'verification_url', 'reset_url', 'frontend_url', 'username')
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