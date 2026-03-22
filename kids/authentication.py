from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .jwt_utils import kids_decode_token
from .models import KidsUser


class KidsJWTAuthentication(BaseAuthentication):
    """
    Authorization: Bearer <kids_access_token>
    Ana site SimpleJWT ile aynı header'ı kullanır; payload `aud=marifetli-kids` ile ayrılır.
    """

    def authenticate(self, request):
        raw = request.META.get("HTTP_AUTHORIZATION", "")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not raw or not raw.startswith("Bearer "):
            return None
        token = raw[7:].strip()
        if not token:
            return None
        payload = kids_decode_token(token)
        if not payload or payload.get("typ") != "access":
            return None
        try:
            user_id = int(payload["sub"])
        except (KeyError, ValueError):
            raise AuthenticationFailed("Geçersiz token.")
        try:
            user = KidsUser.objects.get(pk=user_id, is_active=True)
        except KidsUser.DoesNotExist:
            raise AuthenticationFailed("Kullanıcı bulunamadı.")
        return (user, None)
