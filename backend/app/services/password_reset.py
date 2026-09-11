from __future__ import annotations

import hashlib
import secrets
from typing import Any

import redis

from app.core.config import settings
from app.core.logging import logger
from app.core.redis_client import redis_client

RESET_TOKEN_TTL = 15 * 60


def _token_key(token: str) -> str:
    digest = hashlib.sha256(token.encode()).hexdigest()
    return f"nexus:password-reset:{digest}"


def create_reset_token(user_id: int, client: Any = redis_client) -> str:
    token = secrets.token_urlsafe(32)
    try:
        client.setex(_token_key(token), RESET_TOKEN_TTL, str(user_id))
    except redis.RedisError:
        raise
    if settings.app_env == "development":
        message = (
            f"Development password reset link for user {user_id}: "
            f"{settings.password_reset_frontend_url}?token={token}"
        )
        logger.info(message)
        print(message, flush=True)
    return token


def consume_reset_token(token: str, client: Any = redis_client) -> int | None:
    key = _token_key(token)
    try:
        value = client.getdel(key)
        if value is None:
            return None
        client.delete(key)
    except redis.RedisError:
        raise
    return int(value)
