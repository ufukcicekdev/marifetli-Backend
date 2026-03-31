"""Veli davet e-postaları — `emails.EmailService` (SMTP2GO) ile gönderilir."""

from typing import Optional, Tuple

from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.i18n_catalog import normalize_lang, translate


def kids_invite_signup_url(token) -> str:
    base = (getattr(settings, "KIDS_FRONTEND_URL", None) or "").strip().rstrip("/")
    prefix = (getattr(settings, "KIDS_FRONTEND_PATH_PREFIX", None) or "").strip().strip("/")
    rel = f"/davet/{token}/"
    if prefix:
        path = f"/{prefix}{rel}"
    else:
        path = rel
    if base:
        return f"{base}{path}"
    return path


def send_kids_parent_invite_email(
    *,
    to_email: str,
    signup_url: str,
    class_name: str,
    teacher_display: str,
    expires_days: int,
    language: str | None = None,
) -> Tuple[bool, Optional[str]]:
    from emails.services import EmailService

    lang = normalize_lang(language or "tr")
    cn = (class_name or "").strip() or "-"
    td = (teacher_display or "").strip() or translate(lang, "kids.teacher_label_fallback")
    subject = translate(lang, "kids.invite.subject", class_name=cn)
    link_block = format_html('<a href="{}">{}</a>', signup_url, signup_url)
    greeting = translate(lang, "kids.invite.greeting")
    html_plain = translate(
        lang,
        "kids.invite.html",
        greeting=greeting,
        teacher=td,
        class_name=cn,
        link_block=link_block,
        days=expires_days,
    )
    html = mark_safe(html_plain)
    text = translate(
        lang,
        "kids.invite.text",
        greeting_plain=translate(lang, "kids.invite.greeting_plain"),
        teacher=td,
        class_name=cn,
        url=signup_url,
        days=expires_days,
    )

    sent = EmailService.send_email(
        recipient=to_email,
        subject=subject,
        html_content=html,
        text_content=text,
        metadata={"kids_invite": True, "kids_class_name": class_name},
    )
    if sent.status == "sent":
        return True, None
    return False, (sent.error_message or "E-posta gönderilemedi")
