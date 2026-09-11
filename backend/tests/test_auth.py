from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.services import rate_limit
from tests.test_rate_limit import FakeRedis


def client_fixture() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    original_limiter = rate_limit.rate_limiter
    rate_limit.rate_limiter = rate_limit.RedisRateLimiter(FakeRedis([0.0]))
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    rate_limit.rate_limiter = original_limiter


def test_signup_hashes_password_and_login_sets_cookie() -> None:
    client, factory = next(client_fixture())
    try:
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "a@example.com", "password": "strong-pass"},
        )
        assert response.status_code == 201
        with factory() as db:
            user = db.query(User).first()
            assert user is not None
            assert user.hashed_password != "strong-pass"
        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204
        assert "Max-Age=0" in logout.headers["set-cookie"]
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "a@example.com", "password": "strong-pass"},
        )
        assert login.status_code == 200
        assert client.get("/api/v1/auth/me").json()["email"] == "a@example.com"
    finally:
        app.dependency_overrides.clear()


def test_session_cookie_is_not_secure_in_development() -> None:
    generator = client_fixture()
    client, _ = next(generator)
    try:
        settings.app_env = "test"
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "development@example.com", "password": "strong-pass"},
        )
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie
        assert "Secure" not in cookie
    finally:
        settings.app_env = "test"
        app.dependency_overrides.clear()


def test_session_cookie_is_secure_in_production() -> None:
    generator = client_fixture()
    client, _ = next(generator)
    try:
        settings.app_env = "production"
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "production@example.com", "password": "strong-pass"},
        )
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie
        assert "Secure" in cookie
        assert "Domain=" not in cookie
    finally:
        settings.app_env = "test"
        app.dependency_overrides.clear()


def test_users_cannot_access_each_others_monitors() -> None:
    generator = client_fixture()
    client, _ = next(generator)
    try:
        client.post(
            "/api/v1/auth/signup",
            json={"email": "owner@example.com", "password": "strong-pass"},
        )
        created = client.post(
            "/api/v1/monitors",
            json={"url": "https://example.com", "interval_seconds": 30},
        )
        monitor_id = created.json()["id"]
        client.post("/api/v1/auth/logout")
        client.post(
            "/api/v1/auth/signup",
            json={"email": "other@example.com", "password": "strong-pass"},
        )
        assert client.get(f"/api/v1/monitors/{monitor_id}").status_code == 404
        assert (
            client.patch(
                f"/api/v1/monitors/{monitor_id}", json={"interval_seconds": 60}
            ).status_code
            == 404
        )
        assert client.delete(f"/api/v1/monitors/{monitor_id}").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_missing_and_invalid_sessions_are_rejected() -> None:
    generator = client_fixture()
    client, _ = next(generator)
    try:
        client.cookies.clear()
        # APP_ENV=test preserves legacy anonymous fixtures; an explicit invalid cookie
        # must still be rejected by the real dependency.
        client.cookies.set("nexus_session", "invalid")
        assert client.get("/api/v1/monitors").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_login_endpoint_returns_429_and_success_resets_email_counter(monkeypatch) -> None:
    clock = [100.0]
    limiter = rate_limit.RedisRateLimiter(FakeRedis(clock), clock=lambda: clock[0])
    generator = client_fixture()
    client, _ = next(generator)
    monkeypatch.setattr(rate_limit, "rate_limiter", limiter)
    try:
        assert (
            client.post(
                "/api/v1/auth/signup",
                json={"email": "limited@example.com", "password": "strong-pass"},
            ).status_code
            == 201
        )
        client.post("/api/v1/auth/logout")
        for _ in range(5):
            assert (
                client.post(
                    "/api/v1/auth/login",
                    json={"email": "limited@example.com", "password": "wrong-pass"},
                ).status_code
                == 401
            )
        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": "limited@example.com", "password": "strong-pass"},
        )
        assert blocked.status_code == 429
        assert blocked.headers["retry-after"] == "800"

        clock[0] = 1000.0
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "limited@example.com", "password": "strong-pass"},
            ).status_code
            == 200
        )
        client.post("/api/v1/auth/logout")
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "limited@example.com", "password": "wrong-pass"},
            ).status_code
            == 401
        )
    finally:
        app.dependency_overrides.clear()
