from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.monitoring import MonitorResult


@pytest.fixture
def api_client() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal
    app.dependency_overrides.clear()


def test_create_monitor(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    payload = {
        "url": "http://127.0.0.1:8000/health",
        "http_method": "GET",
        "expected_status_code": 200,
        "interval_seconds": 30,
        "timeout_seconds": 5,
        "active": True,
    }

    response = client.post("/api/v1/monitors", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["url"] == payload["url"]
    assert data["http_method"] == "GET"
    assert data["active"] is True


def test_list_and_retrieve_monitor(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    payload = {
        "url": "http://127.0.0.1:8001/health",
        "http_method": "GET",
        "expected_status_code": 200,
        "interval_seconds": 30,
        "timeout_seconds": 5,
        "active": True,
    }

    created = client.post("/api/v1/monitors", json=payload)
    monitor_id = created.json()["id"]

    list_response = client.get("/api/v1/monitors")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = client.get(f"/api/v1/monitors/{monitor_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == monitor_id


def test_update_monitor(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    created = client.post(
        "/api/v1/monitors",
        json={
            "url": "http://127.0.0.1:8002/health",
            "http_method": "GET",
            "expected_status_code": 200,
            "interval_seconds": 30,
            "timeout_seconds": 5,
            "active": True,
        },
    )
    monitor_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/monitors/{monitor_id}",
        json={"expected_status_code": 204, "interval_seconds": 45, "active": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["expected_status_code"] == 204
    assert data["interval_seconds"] == 45
    assert data["active"] is False


def test_activate_and_deactivate_monitor(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = api_client
    created = client.post(
        "/api/v1/monitors",
        json={
            "url": "http://127.0.0.1:8003/health",
            "http_method": "GET",
            "expected_status_code": 200,
            "interval_seconds": 30,
            "timeout_seconds": 5,
        },
    )
    monitor_id = created.json()["id"]

    deactivate = client.post(f"/api/v1/monitors/{monitor_id}/deactivate")
    assert deactivate.status_code == 200
    assert deactivate.json()["active"] is False

    activate = client.post(f"/api/v1/monitors/{monitor_id}/activate")
    assert activate.status_code == 200
    assert activate.json()["active"] is True


def test_delete_monitor(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    created = client.post(
        "/api/v1/monitors",
        json={
            "url": "http://127.0.0.1:8004/health",
            "http_method": "GET",
            "expected_status_code": 200,
            "interval_seconds": 30,
            "timeout_seconds": 5,
        },
    )
    monitor_id = created.json()["id"]

    delete_response = client.delete(f"/api/v1/monitors/{monitor_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/monitors/{monitor_id}")
    assert get_response.status_code == 404


def test_monitor_history(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, session_factory = api_client
    created = client.post(
        "/api/v1/monitors",
        json={
            "url": "http://127.0.0.1:8005/health",
            "http_method": "GET",
            "expected_status_code": 200,
            "interval_seconds": 30,
            "timeout_seconds": 5,
        },
    )
    monitor_id = created.json()["id"]

    with session_factory() as session:
        session.add(
            MonitorResult(
                endpoint_id=monitor_id,
                http_status=200,
                latency_ms=120,
                response_size=512,
                success=True,
                error_category=None,
                error_details=None,
            )
        )
        session.commit()

    response = client.get(f"/api/v1/monitors/{monitor_id}/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["endpoint_id"] == monitor_id
    assert data[0]["success"] is True


def test_invalid_input_returns_422(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    payload = {
        "url": "ftp://example.com",
        "http_method": "GET",
        "expected_status_code": 200,
    }

    response = client.post("/api/v1/monitors", json=payload)
    assert response.status_code == 422


def test_missing_monitor_returns_404(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    response = client.get("/api/v1/monitors/999999")
    assert response.status_code == 404


def test_list_accepts_filters(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    client.post(
        "/api/v1/monitors",
        json={
            "url": "http://127.0.0.1:8006/health",
            "http_method": "GET",
            "expected_status_code": 200,
            "interval_seconds": 30,
            "timeout_seconds": 5,
            "active": True,
        },
    )
    client.post(
        "/api/v1/monitors",
        json={
            "url": "http://127.0.0.1:8007/health",
            "http_method": "POST",
            "expected_status_code": 204,
            "interval_seconds": 45,
            "timeout_seconds": 7,
            "active": False,
        },
    )

    active_response = client.get("/api/v1/monitors?active=true")
    inactive_response = client.get("/api/v1/monitors?active=false")

    assert active_response.status_code == 200
    assert inactive_response.status_code == 200
    assert len(active_response.json()) == 1
    assert len(inactive_response.json()) == 1
