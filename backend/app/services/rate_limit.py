from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import redis
from fastapi import HTTPException, Request, status

from app.core.redis_client import redis_client
from app.schemas.auth import AuthCredentials


@dataclass(frozen=True)
class RateLimit:
    requests: int
    window_seconds: int


class RedisRateLimiter:
    """Fixed-window Redis limiter shared by all backend instances."""

    def __init__(
        self,
        client: Any,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.client = client
        self.clock = clock

    def check(self, key: str, limit: RateLimit) -> int:
        now = int(self.clock())
        window_start = now - (now % limit.window_seconds)
        redis_key = f"nexus:rate-limit:{key}:{window_start}"
        try:
            count = int(self.client.incr(redis_key))
            if count == 1:
                self.client.expire(redis_key, limit.window_seconds)
        except redis.RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is temporarily unavailable. Please try again shortly.",
                headers={"Retry-After": "30"},
            ) from exc

        if count > limit.requests:
            retry_after = max(1, window_start + limit.window_seconds - now)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        return count

    def reset(self, key: str) -> None:
        try:
            keys = list(self.client.scan_iter(match=f"nexus:rate-limit:{key}:*"))
            if keys:
                self.client.delete(*keys)
        except redis.RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is temporarily unavailable. Please try again shortly.",
                headers={"Retry-After": "30"},
            ) from exc


rate_limiter = RedisRateLimiter(redis_client)

LOGIN_EMAIL_LIMIT = RateLimit(requests=5, window_seconds=15 * 60)
LOGIN_IP_LIMIT = RateLimit(requests=20, window_seconds=60 * 60)
SIGNUP_EMAIL_LIMIT = RateLimit(requests=3, window_seconds=60 * 60)
SIGNUP_IP_LIMIT = RateLimit(requests=10, window_seconds=15 * 60)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def check_login_rate_limit(request: Request, payload: AuthCredentials) -> None:
    email = payload.email.lower()
    rate_limiter.check(f"login:email:{email}", LOGIN_EMAIL_LIMIT)
    rate_limiter.check(f"login:ip:{_client_ip(request)}", LOGIN_IP_LIMIT)


def check_signup_rate_limit(request: Request, payload: AuthCredentials) -> None:
    email = payload.email.lower()
    rate_limiter.check(f"signup:email:{email}", SIGNUP_EMAIL_LIMIT)
    rate_limiter.check(f"signup:ip:{_client_ip(request)}", SIGNUP_IP_LIMIT)
