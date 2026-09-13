from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "NEXUS" in response.json()["message"]


def test_live_health_endpoint() -> None:
    response = client.get("/api/v1/health/live", headers={"X-Request-ID": "test-request-id"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"] == "test-request-id"


def test_ready_health_endpoint() -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert "status" in response.json()


def test_metrics_health_endpoint() -> None:
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
    try:
        response = client.get("/api/v1/health/metrics")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["redis"]["ok"] is True
    assert "depth" in payload["queue"]
    assert "active" in payload["monitors"]
    assert "heartbeat" in payload["worker"]
    assert "recent_success_rate_percentage" in payload["checks"]
