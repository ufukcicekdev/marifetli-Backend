"""Kids API istek kullanıcısı: öğrenci `KidsUser`, veli/öğretmen/yönetim `users.User`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from users.models import KidsPortalRole

from .models import KidsUser

if TYPE_CHECKING:
    from users.models import User as UserType

_MainUser = get_user_model()


def is_kids_student_user(u) -> bool:
    return isinstance(u, KidsUser)


def is_main_user(u) -> bool:
    return isinstance(u, _MainUser)


def is_kids_parent_user(u) -> bool:
    return (
        is_main_user(u)
        and (getattr(u, "kids_portal_role", None) or "") == KidsPortalRole.PARENT
    )


def is_kids_teacher_or_admin_user(u) -> bool:
    if not is_main_user(u):
        return False
    if u.is_superuser or u.is_staff:
        return True
    r = (getattr(u, "kids_portal_role", None) or "").strip()
    return r in (KidsPortalRole.TEACHER, KidsPortalRole.KIDS_ADMIN)


def is_kids_admin_user(u) -> bool:
    if not is_main_user(u):
        return False
    if u.is_superuser or u.is_staff:
        return True
    return (getattr(u, "kids_portal_role", None) or "") == KidsPortalRole.KIDS_ADMIN


def may_access_kids_with_main_jwt(u: UserType) -> bool:
    """Normal kayıt: kids_portal_role boş → Kids API’ye giremez."""
    if not u or not u.is_active or getattr(u, "is_deactivated", False):
        return False
    if u.is_superuser or u.is_staff:
        return True
    r = (getattr(u, "kids_portal_role", None) or "").strip()
    return r in (KidsPortalRole.TEACHER, KidsPortalRole.PARENT, KidsPortalRole.KIDS_ADMIN)
