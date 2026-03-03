"""
Social auth pipeline: Google (ve diğer sağlayıcılar) ile giriş yapan kullanıcıların
e-postası zaten doğrulanmış kabul edilir.
"""


def set_social_user_verified(backend, user, **kwargs):
    if user and backend.name == "google-oauth2":
        if not getattr(user, "is_verified", False):
            user.is_verified = True
            user.save(update_fields=["is_verified"])
    return {"user": user}
