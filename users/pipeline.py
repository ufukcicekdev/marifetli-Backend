"""
Social auth pipeline: Google (ve diğer sağlayıcılar) ile giriş.

- Kullanıcı yoksa: email ile yeni kullanıcı oluşturulur, profil ve bildirim ayarları açılır.
- Kullanıcı varsa (email veya daha önce bu Google hesabıyla giriş): mevcut kullanıcıya giriş yapılır.
E-posta doğrulanmış kabul edilir; username email'den türetilir.

Son adımda JWT üretilip frontend'e yönlendirilir (session'a hiç güvenilmez).
"""
from django.conf import settings
from django.shortcuts import redirect
from urllib.parse import urlencode
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from .models import UserProfile, UserNotificationPreference

User = get_user_model()


def get_username_from_email(strategy, details, *args, **kwargs):
    """Google'dan gelen email ile username yoksa email'in local part'ını kullan (benzersiz yapılacak)."""
    if details.get("username"):
        return
    email = details.get("email") or ""
    if not email:
        return
    base = email.split("@")[0].replace(".", "_")[:140]
    username = base
    n = 0
    while User.objects.filter(username=username).exists():
        n += 1
        username = f"{base}{n}"[:150]
    details["username"] = username
    return {"details": details}


def create_user_with_email(strategy, details, backend, user=None, *args, **kwargs):
    """
    Google'dan gelen email'e göre kullanıcı bul veya oluştur.
    Session'dan gelen user sadece email eşleşiyorsa kabul edilir; farklı Gmail ile girişte
    eski kullanıcıyı kullanmamak için her zaman details['email'] ile eşleştiriyoruz.
    """
    email = details.get("email")
    if not email:
        return
    # Session'dan gelen user sadece bu Google hesabının email'i ile aynıysa kullan
    if user and getattr(user, "email", None) == email:
        return {"is_new": False}
    # Aksi halde bu Google hesabının email'ine göre bul veya oluştur
    username = details.get("username") or (email.split("@")[0].replace(".", "_")[:150])
    existing = User.objects.filter(email=email).first()
    if existing:
        return {"is_new": False, "user": existing}
    user = User.objects.create_user(
        email=email,
        username=username,
        password=None,
        first_name=details.get("first_name", ""),
        last_name=details.get("last_name", ""),
    )
    return {"is_new": True, "user": user}


def set_social_user_verified(backend, user, is_new=False, **kwargs):
    if not user:
        return {}
    if backend.name == "google-oauth2":
        if not getattr(user, "is_verified", False):
            user.is_verified = True
            user.save(update_fields=["is_verified"])
    if is_new:
        UserProfile.objects.get_or_create(user=user)
        UserNotificationPreference.objects.get_or_create(user=user)
    return {"user": user}


def redirect_to_frontend_with_jwt(backend, user, **kwargs):
    """
    Pipeline'ın son adımı: Session kullanmadan JWT üretir ve frontend /auth/callback#... ile yönlendirir.
    HttpResponse döndüğü için social_django bu cevabı döner, LOGIN_REDIRECT_URL atlanır.
    """
    if not user or backend.name != "google-oauth2":
        return
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    refresh_str = str(refresh)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    params = urlencode({"access": access, "refresh": refresh_str})
    return redirect(f"{frontend_url}/auth/callback#{params}")
