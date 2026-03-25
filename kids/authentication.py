from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from .auth_utils import may_access_kids_with_main_jwt
from .jwt_utils import kids_decode_token
from .models import KidsUser


def _extract_bearer(request) -> str | None:
    raw = request.META.get("HTTP_AUTHORIZATION", "")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if not raw or not raw.startswith("Bearer "):
        return None
    token = raw[7:].strip()
    return token or None


class KidsJWTAuthentication(BaseAuthentication):
    """
    1) Kids JWT → yalnızca öğrenci (`KidsUser`).
    2) Ana site SimpleJWT → `users.User` ve `kids_portal_role` (veya staff) gerekir.
    """

    def authenticate(self, request):
        token = _extract_bearer(request)
        if not token:
            return None
        payload = kids_decode_token(token)
        if payload and payload.get("typ") == "access":
            try:
                user_id = int(payload["sub"])
            except (KeyError, ValueError):
                raise AuthenticationFailed("Geçersiz token.")
            try:
                user = KidsUser.objects.get(pk=user_id, is_active=True)
            except KidsUser.DoesNotExist:
                raise AuthenticationFailed("Kullanıcı bulunamadı.")
            return (user, None)

        jwt_auth = JWTAuthentication()
        try:
            result = jwt_auth.authenticate(request)
        except InvalidToken:
            return None
        if result is None:
            return None
        main_user, validated = result
        if not main_user.is_active:
            raise AuthenticationFailed("Hesap pasif.")
        if getattr(main_user, "is_deactivated", False):
            raise AuthenticationFailed("Hesap devre dışı.")
        if not may_access_kids_with_main_jwt(main_user):
            return None
        return (main_user, validated)


class KidsOrMainSiteStaffJWTAuthentication(KidsJWTAuthentication):
    """Geriye dönük isim; staff `kids_portal_role` ile veya `is_staff` ile zaten geçer."""

    pass
