"""Veli davet e-postaları — `emails.EmailService` (SMTP2GO) ile gönderilir."""

from typing import Optional, Tuple

from django.conf import settings
from django.utils.html import format_html


def kids_invite_signup_url(token) -> str:
    base = (getattr(settings, "KIDS_FRONTEND_URL", None) or "").strip().rstrip("/")
    if base:
        return f"{base}/davet/{token}/"
    return f"/davet/{token}/"


def send_kids_parent_invite_email(
    *,
    to_email: str,
    signup_url: str,
    class_name: str,
    teacher_display: str,
    expires_days: int,
) -> Tuple[bool, Optional[str]]:
    from emails.services import EmailService

    cn = class_name or "Sınıf"
    td = teacher_display or "Öğretmeniniz"
    subject = f"Marifetli Kids — {cn} daveti"
    link_block = format_html('<a href="{}">{}</a>', signup_url, signup_url)
    html = format_html(
        "<p>Merhaba,</p>"
        "<p><strong>{}</strong>, <strong>{}</strong> sınıfı için Marifetli Kids üzerinden "
        "öğrenci kaydı daveti gönderdi.</p>"
        "<p>Aşağıdaki bağlantıyı kullanarak çocuğunuzun hesabını oluşturabilirsiniz "
        "(veya mevcut öğrenci hesabıyla bu sınıfa katılabilirsiniz):</p>"
        "<p>{}</p>"
        "<p>Bu davet yaklaşık <strong>{} gün</strong> geçerlidir.</p>"
        "<p>Marifetli Kids — çocuklar için güvenli proje ve ödev alanı</p>",
        td,
        cn,
        link_block,
        expires_days,
    )
    text = (
        f"Merhaba,\n\n"
        f"{teacher_display}, {class_name} sınıfı için Marifetli Kids daveti gönderdi.\n\n"
        f"Kayıt bağlantısı:\n{signup_url}\n\n"
        f"Davet yaklaşık {expires_days} gün geçerlidir.\n"
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

