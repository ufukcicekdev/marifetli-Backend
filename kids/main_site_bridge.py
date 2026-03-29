"""Veli hesabını `users.User` + `kids_portal_role=parent` ile oluşturur / günceller."""

from __future__ import annotations

import re

from django.contrib.auth import get_user_model

from users.models import KidsPortalRole

MainUser = get_user_model()


def unique_username_from_email(email: str) -> str:
    local = (email.split("@", 1)[0] if "@" in email else email) or "user"
    base = re.sub(r"[^a-zA-Z0-9_]", "_", local)[:40].strip("_") or "user"
    candidate = base
    n = 0
    while MainUser.objects.filter(username=candidate).exists():
        n += 1
        candidate = f"{base}_{n}"
    return candidate


def provision_kids_parent_user(
    *,
    email: str,
    first_name: str,
    last_name: str,
    phone: str,
    raw_password: str,
) -> MainUser:
    """Davet akışı: veli ana sitede hesaplanır; `kids_portal_role=parent` atanır."""
    email_norm = (email or "").strip().lower()
    if not email_norm or "@" not in email_norm:
        raise ValueError("Geçerli veli e-postası gerekli.")
    existing = MainUser.objects.filter(email__iexact=email_norm).first()
    if existing:
        if not raw_password or not existing.check_password(raw_password):
            raise ValueError(
                "Bu e-posta Marifetli ana sitede kayıtlı; şifre eşleşmiyor veya eksik."
            )
        existing.kids_portal_role = KidsPortalRole.PARENT
        existing.is_verified = True
        if first_name:
            existing.first_name = first_name[:150]
        if last_name:
            existing.last_name = last_name[:150]
        existing.save(
            update_fields=[
                "kids_portal_role",
                "is_verified",
                "first_name",
                "last_name",
                "updated_at",
            ]
        )
        # telefon ana User’da yoksa KidsUser velide tutulmuyor artık — ileride User’a alan eklenebilir.
        return existing
    if not raw_password:
        raise ValueError("Yeni veli hesabı için şifre gerekli.")
    return MainUser.objects.create_user(
        username=unique_username_from_email(email_norm),
        email=email_norm,
        password=raw_password,
        first_name=(first_name or "")[:150],
        last_name=(last_name or "")[:150],
        is_verified=True,
        kids_portal_role=KidsPortalRole.PARENT,
    )
