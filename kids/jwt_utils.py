from datetime import datetime, timezone

import jwt
from django.conf import settings

KIDS_JWT_AUDIENCE = "marifetli-kids"


def kids_encode_token(user_id: int, *, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    if token_type == "access":
        exp = now + settings.KIDS_JWT_ACCESS_LIFETIME
    elif token_type == "refresh":
        exp = now + settings.KIDS_JWT_REFRESH_LIFETIME
    else:
        raise ValueError("token_type must be access or refresh")
    payload = {
        "sub": str(user_id),
        "aud": KIDS_JWT_AUDIENCE,
        "typ": token_type,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(
        payload,
        settings.KIDS_JWT_SIGNING_KEY,
        algorithm="HS256",
    )


def kids_decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.KIDS_JWT_SIGNING_KEY,
            algorithms=["HS256"],
            audience=KIDS_JWT_AUDIENCE,
        )
    except jwt.PyJWTError:
        return None
