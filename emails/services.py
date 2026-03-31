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

from core.i18n_catalog import email_bundle, normalize_lang, translate
from core.i18n_resolve import language_for_kids_student, language_from_user

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


def _format_email_i18n_strings(ei: dict, fmt: dict) -> dict[str, str]:
    """HTML içinde {{ email_i18n.xxx }} — {username} vb. yer tutucuları doldurur."""
    out: dict[str, str] = {}
    for k, v in ei.items():
        if not isinstance(v, str):
            out[k] = str(v)
            continue
        try:
            out[k] = v.format(**fmt) if "{" in v else v
        except (KeyError, ValueError):
            out[k] = v
    return out


def _email_format_kwargs(context: dict) -> dict:
    """Şablon subject / düz metin format() için güvenli alanlar."""
    ctx = context or {}
    u = ctx.get("user")
    username = ""
    if u is not None:
        username = getattr(u, "username", None) or ""
    if not username:
        username = str(ctx.get("username") or "")
    return {
        "site_name": ctx.get("site_name") or "Marifetli",
        "username": username,
        "verification_url": str(ctx.get("verification_url") or ""),
        "reset_url": str(ctx.get("reset_url") or ""),
        "frontend_url": str(ctx.get("frontend_url") or ""),
        "message": str(ctx.get("message") or ""),
        "display_name": str(ctx.get("display_name") or ""),
        "teacher_email": str(ctx.get("teacher_email") or ""),
        "temp_password": str(ctx.get("temp_password") or ""),
        "login_url": str(ctx.get("login_url") or ""),
        "reset_hint_url": str(ctx.get("reset_hint_url") or ""),
        "parent_name": str(ctx.get("parent_name") or ""),
        "student_name": str(ctx.get("student_name") or ""),
        "class_name": str(ctx.get("class_name") or ""),
        "test_title": str(ctx.get("test_title") or ""),
        "teacher_name": str(ctx.get("teacher_name") or ""),
        "teacher_subject": str(ctx.get("teacher_subject") or ""),
        "duration_text": str(ctx.get("duration_text") or ""),
        "parent_panel_url": str(ctx.get("parent_panel_url") or ""),
        "display_name": str(ctx.get("display_name") or ""),
    }


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
    def send_template_email(recipient, template_type, context, from_email=None, language=None):
        """
        Send email using a stored template.
        Dil: `language` veya alıcı `user.preferred_language`; şablon metinleri `core.i18n_catalog`.
        """
        try:
            template = EmailTemplate.objects.get(template_type=template_type, is_active=True)
        except EmailTemplate.DoesNotExist:
            logger.error(f"Email template '{template_type}' not found")
            return None

        base_ctx = _get_email_base_context()
        merged_context = {**base_ctx, **(context or {})}
        context = merged_context

        if language is not None:
            lang = normalize_lang(language)
        elif context.get("user") is not None:
            lang = language_from_user(context["user"])
        else:
            lang = "tr"
        fmt = _email_format_kwargs(context)
        ei = email_bundle(template_type, lang)
        context["email_i18n"] = _format_email_i18n_strings(ei, fmt)
        context["html_lang"] = lang

        if context.get("subject_override"):
            subject = str(context["subject_override"])
        else:
            subj_tpl = ei.get("subject") or template.subject
            try:
                subject = subj_tpl.format(**fmt)
            except (KeyError, ValueError):
                try:
                    subject = template.subject.format(**context)
                except Exception:
                    subject = template.subject

        html_content = render_to_string(template.html_content, context) if template.html_content else ""
        txt_tpl = ei.get("text_plain") or (template.text_content or "")
        try:
            text_content = txt_tpl.format(**fmt) if txt_tpl else ""
        except (KeyError, ValueError):
            try:
                text_content = (
                    template.text_content.format(**context) if context and template.text_content else (template.text_content or "")
                )
            except KeyError:
                text_content = template.text_content or ""
        
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
            context=context,
            language=language_from_user(user),
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
            context=context,
            language=language_from_user(user),
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
            language=language_for_kids_student(kids_user),
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
            context=context,
            language=language_from_user(user),
        )
    
    @staticmethod
    def send_kids_teacher_welcome_email(
        *,
        to_email: str,
        first_name: str,
        temp_password: str,
        login_url: str,
        reset_hint_url: str,
        language: str | None = None,
    ):
        """
        Kids yönetiminden oluşturulan öğretmene geçici şifre e-postası.
        `emails/kids_teacher_welcome_email.html` + DB şablonu `kids_teacher_welcome`; yoksa düz HTML fallback.
        """
        lang = normalize_lang(language)
        display_name = (first_name or "").strip() or translate(lang, "kids.teacher_label_fallback")
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
            language=lang,
        )
        if sent is not None:
            return sent

        logger.warning(
            "Email template 'kids_teacher_welcome' bulunamadı; düz metin/HTML fallback kullanılıyor. "
            "Şablon için: python manage.py populate_email_templates"
        )
        subject = translate(lang, "email.kids_teacher_welcome.subject")
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
    def send_kids_parent_new_test_email(
        *,
        to_email: str,
        parent_name: str,
        student_name: str,
        class_name: str,
        test_title: str,
        teacher_name: str,
        teacher_subject: str,
        duration_text: str,
        parent_panel_url: str,
        language: str | None = None,
    ):
        """Veliye yeni test yayınlandığında bilgilendirme e-postası gönderir."""
        lang = normalize_lang(language)
        context = {
            "parent_name": (parent_name or "").strip() or translate(lang, "kids.parent_label_fallback"),
            "student_name": (student_name or "").strip() or translate(lang, "kids.student_label_fallback"),
            "class_name": (class_name or "").strip() or "-",
            "test_title": (test_title or "").strip() or "Test",
            "teacher_name": (teacher_name or "").strip() or translate(lang, "kids.teacher_label_fallback"),
            "teacher_subject": (teacher_subject or "").strip() or translate(lang, "kids.test.teacher_subject_fallback"),
            "duration_text": (duration_text or "").strip() or "—",
            "parent_panel_url": (parent_panel_url or "").strip(),
        }
        sent = EmailService.send_template_email(
            recipient=to_email,
            template_type="kids_parent_new_test",
            context=context,
            language=lang,
        )
        if sent is not None:
            return sent

        logger.warning(
            "Email template 'kids_parent_new_test' bulunamadı; düz metin/HTML fallback kullanılıyor. "
            "Şablon için: python manage.py populate_email_templates"
        )

        subject = translate(lang, "email.kids_parent_new_test.subject", test_title=context["test_title"])
        html = (
            f"<p>Merhaba {context['parent_name']},</p>"
            f"<p><strong>{context['class_name']}</strong> sınıfı için yeni bir test yayınlandı.</p>"
            f"<p><strong>Test:</strong> {context['test_title']}<br/>"
            f"<strong>Öğretmen:</strong> {context['teacher_name']}<br/>"
            f"<strong>Branş:</strong> {context['teacher_subject']}<br/>"
            f"<strong>Süre:</strong> {context['duration_text']}<br/>"
            f"<strong>Öğrenci:</strong> {context['student_name']}</p>"
            f"<p>Detaylar: <a href=\"{context['parent_panel_url']}\">{context['parent_panel_url']}</a></p>"
        )
        text = (
            f"Merhaba {context['parent_name']},\n\n"
            f"{context['class_name']} sınıfı için yeni bir test yayınlandı.\n\n"
            f"Test: {context['test_title']}\n"
            f"Öğretmen: {context['teacher_name']}\n"
            f"Branş: {context['teacher_subject']}\n"
            f"Süre: {context['duration_text']}\n"
            f"Öğrenci: {context['student_name']}\n\n"
            f"Detaylar: {context['parent_panel_url']}\n"
        )
        return EmailService.send_email(
            recipient=to_email,
            subject=subject,
            html_content=html,
            text_content=text,
            metadata={"kids_parent_new_test": True, "template_fallback": True},
        )

    @staticmethod
    def send_notification_email(user, message, notification_type='general', *, language=None):
        """Genel bildirim e-postası — konu ve şablon dili alıcı tercihine göre."""
        lang = normalize_lang(language) if language else language_from_user(user)
        lk = f"email.notif_label.{notification_type}"
        lbl = translate(lang, lk)
        if lbl == lk:
            lbl = translate(lang, "email.notif_label.general")
        subj = translate(lang, "main.email.notification_subject", preview=message[:50])
        context = {
            "user": user,
            "message": message,
            "notification_type": notification_type,
            "notification_type_label": lbl,
            "frontend_url": getattr(settings, "FRONTEND_URL", ""),
            "subject_override": subj,
        }
        return EmailService.send_template_email(
            recipient=user.email,
            template_type="notification",
            context=context,
            language=lang,
        )