"""
Kullanıcı / sınıf dilinden i18n katalog koduna (tr, en, ge) çözümleme.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .i18n_catalog import normalize_lang

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser


def language_from_user(user: AbstractBaseUser | None) -> str:
    if user is None:
        return "tr"
    raw = getattr(user, "preferred_language", None) or ""
    return normalize_lang(str(raw))


def language_for_kids_user_main(parent_or_teacher: AbstractBaseUser | None) -> str:
    """Veli / öğretmen ana site User kaydı."""
    return language_from_user(parent_or_teacher)


def language_for_kids_student(student) -> str:
    """
    Öğrenci: kayıtlı olduğu sınıflardan birinin dilini kullan (ilk kayıt).
    KidsUser — tercih alanı yok; sınıf dili kaynak.
    """
    if student is None:
        return "tr"
    try:
        from kids.models import KidsEnrollment

        row = (
            KidsEnrollment.objects.filter(student_id=student.pk)
            .select_related("kids_class")
            .order_by("id")
            .first()
        )
        if row and row.kids_class_id:
            raw = getattr(row.kids_class, "language", None) or ""
            return normalize_lang(str(raw))
    except Exception:
        pass
    return "tr"


def language_for_kids_recipient(
    *,
    recipient_student=None,
    recipient_user: AbstractBaseUser | None = None,
    fallback_lang: str | None = None,
) -> str:
    if recipient_user is not None:
        return language_from_user(recipient_user)
    if recipient_student is not None:
        return language_for_kids_student(recipient_student)
    if fallback_lang:
        return normalize_lang(fallback_lang)
    return "tr"
