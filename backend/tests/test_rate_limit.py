import pytest
import redis
from fastapi import HTTPException

from app.services.rate_limit import RateLimit, RedisRateLimiter


class FakeRedis:
    def __init__(self, clock: list[float]) -> None:
        self.clock = clock
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}
        self.unavailable = False

    def incr(self, key: str) -> int:
        if self.unavailable:
            raise redis.RedisError("redis unavailable")
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds

    def scan_iter(self, *, match: str):
        prefix = match.removesuffix("*")
        return (key for key in self.values if key.startswith(prefix))

    def delete(self, *keys: str) -> None:
        for key in keys:
            self.values.pop(key, None)


def test_rate_limit_returns_retry_after_and_resets_after_window() -> None:
    clock = [100.0]
    limiter = RedisRateLimiter(FakeRedis(clock), clock=lambda: clock[0])
    limit = RateLimit(requests=2, window_seconds=60)

    limiter.check("login:email:user@example.com", limit)
    limiter.check("login:email:user@example.com", limit)
    with pytest.raises(HTTPException) as error:
        limiter.check("login:email:user@example.com", limit)
    assert error.value.status_code == 429
    assert error.value.headers == {"Retry-After": "20"}

    clock[0] = 160.0
    assert limiter.check("login:email:user@example.com", limit) == 1


def test_successful_login_counter_can_be_reset() -> None:
    clock = [100.0]
    redis_client = FakeRedis(clock)
    limiter = RedisRateLimiter(redis_client, clock=lambda: clock[0])
    limit = RateLimit(requests=2, window_seconds=60)

    limiter.check("login:email:user@example.com", limit)
    limiter.reset("login:email:user@example.com")
    assert limiter.check("login:email:user@example.com", limit) == 1


def test_redis_failure_fails_closed() -> None:
    clock = [100.0]
    redis_client = FakeRedis(clock)
    redis_client.unavailable = True
    limiter = RedisRateLimiter(redis_client, clock=lambda: clock[0])

    with pytest.raises(HTTPException) as error:
        limiter.check("login:ip:127.0.0.1", RateLimit(requests=1, window_seconds=60))
    assert error.value.status_code == 503
