"""
Social auth pipeline: Google (ve diğer sağlayıcılar) ile giriş yapan kullanıcıların
e-postası zaten doğrulanmış kabul edilir. Username email'den türetilir.
"""
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
    """User.USERNAME_FIELD=email olduğu için email ve username ile kullanıcı oluştur veya mevcut kullanıcıyı döndür."""
    if user:
        return {"is_new": False}
    email = details.get("email")
    if not email:
        return
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
