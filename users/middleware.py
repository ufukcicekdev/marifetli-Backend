from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.contrib.auth import get_user_model, logout
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


class ClearSessionBeforeGoogleOAuthMiddleware(MiddlewareMixin):
    """
    Google OAuth başlatma isteğinde (login/google-oauth2/) session'ı temizler.
    Böylece eski link veya doğrudan bu URL ile gidilse bile farklı Gmail ile doğru kullanıcıya giriş yapılır.
    """
    def process_request(self, request):
        if request.method != "GET":
            return None
        path = request.path.rstrip("/")
        if path.endswith("/api/auth/login/google-oauth2"):
            logout(request)
        return None


class JWTMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip JWT authentication for public endpoints
        if request.path.startswith('/api/auth/') or request.path.startswith('/admin/'):
            return None

        jwt_auth = JWTAuthentication()

        try:
            validated_token = jwt_auth.get_validated_token(request)
            user = jwt_auth.get_user(validated_token)
            request.user = user
        except (InvalidToken, TokenError):
            # Token is invalid, return unauthorized response
            return JsonResponse({
                'error': 'Invalid or expired token'
            }, status=401)

        return None