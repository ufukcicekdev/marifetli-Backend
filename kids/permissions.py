from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

from .auth_utils import is_kids_admin_user, is_kids_parent_user, is_kids_student_user, is_kids_teacher_or_admin_user

_MainUser = get_user_model()


class IsKidsAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_kids_admin_user(request.user)


class IsKidsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_kids_teacher_or_admin_user(request.user)


class IsKidsStudent(BasePermission):
    def has_permission(self, request, view):
        return is_kids_student_user(request.user)


class IsKidsParent(BasePermission):
    def has_permission(self, request, view):
        return is_kids_parent_user(request.user)