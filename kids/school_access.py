"""Okul erişim sorguları: yönetim, üyelik ve eski teacher FK."""

from __future__ import annotations

from django.db.models import Q

from .auth_utils import is_kids_admin_user
from .models import KidsEnrollment, KidsSchool


def schools_queryset_for_main_user(user):
    """Öğretmen: üye olduğu + eski `KidsSchool.teacher` kayıtları. Yönetim: tüm okullar."""
    if is_kids_admin_user(user):
        return KidsSchool.objects.all().order_by("name", "-id")
    return (
        KidsSchool.objects.filter(
            Q(teacher_id=user.pk)
            | Q(school_teachers__user_id=user.pk, school_teachers__is_active=True)
        )
        .distinct()
        .order_by("name", "-id")
    )


def enrolled_distinct_student_count_for_school_year(school_id: int, academic_year: str) -> int:
    """Sınıf etiketi verilen yılla eşleşen sınıflardaki benzersiz öğrenci sayısı."""
    ay = (academic_year or "").strip()
    if not ay:
        return 0
    return (
        KidsEnrollment.objects.filter(
            kids_class__school_id=school_id,
            kids_class__academic_year_label=ay,
        )
        .values("student_id")
        .distinct()
        .count()
    )
