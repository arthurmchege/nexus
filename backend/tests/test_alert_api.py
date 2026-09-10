from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_failed_results_create_alert_and_recovery_resolves_it(
    api_client: TestClient,
) -> None:
    created = api_client.post(
        "/api/v1/monitors",
        json={
            "url": "http://127.0.0.1:8000/health",
            "failure_threshold": 2,
            "recovery_threshold": 2,
        },
    )
    assert created.status_code == 201
    monitor_id = created.json()["id"]
    failed_payload = {
        "http_status": 503,
        "latency_ms": 100,
        "response_size": 0,
        "success": False,
        "error_category": "unexpected_status",
    }

    assert (
        api_client.post(f"/api/v1/monitors/{monitor_id}/results", json=failed_payload).status_code
        == 200
    )
    assert (
        api_client.post(f"/api/v1/monitors/{monitor_id}/results", json=failed_payload).status_code
        == 200
    )

    open_alerts = api_client.get("/api/v1/alerts?status=open")
    assert open_alerts.status_code == 200
    assert len(open_alerts.json()) == 1
    assert open_alerts.json()[0]["monitor_id"] == monitor_id

    success_payload = {
        "http_status": 200,
        "latency_ms": 80,
        "response_size": 10,
        "success": True,
    }
    assert (
        api_client.post(f"/api/v1/monitors/{monitor_id}/results", json=success_payload).status_code
        == 200
    )
    assert (
        api_client.post(f"/api/v1/monitors/{monitor_id}/results", json=success_payload).status_code
        == 200
    )

    resolved_alerts = api_client.get("/api/v1/alerts?status=resolved")
    assert resolved_alerts.status_code == 200
    assert resolved_alerts.json()[0]["status"] == "resolved"
