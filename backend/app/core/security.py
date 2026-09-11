from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

COOKIE_NAME = "nexus_session"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(user_id: int) -> str:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "iat": issued_at, "exp": expires_at},
        settings.jwt_secret_key,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    return int(payload["sub"])


def decode_access_token_claims(token: str) -> dict[str, object]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
