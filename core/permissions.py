from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


class IsVerified(BasePermission):
    """
    Sadece e-posta adresi doğrulanmış kullanıcılara izin verir.
    Gönderi paylaşma, yorum, beğeni vb. için IsAuthenticated ile birlikte kullanın.
    """
    message = 'Bu işlem için e-posta adresinizi doğrulamanız gerekiyor.'
    code = 'email_not_verified'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True  # IsAuthenticated 403 döndürsün
        if getattr(request.user, 'is_verified', False):
            return True
        raise PermissionDenied(detail={
            'code': self.code,
            'message': self.message,
        })
