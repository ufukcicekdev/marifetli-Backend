from rest_framework.permissions import BasePermission

from .models import KidsUserRole


class IsKidsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u
            and getattr(u, "is_authenticated", False)
            and getattr(u, "role", None) == KidsUserRole.ADMIN
        )


class IsKidsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u
            and getattr(u, "is_authenticated", False)
            and getattr(u, "role", None) in (KidsUserRole.TEACHER, KidsUserRole.ADMIN)
        )


class IsKidsStudent(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u
            and getattr(u, "is_authenticated", False)
            and getattr(u, "role", None) == KidsUserRole.STUDENT
        )
