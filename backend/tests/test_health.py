from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "NEXUS" in response.json()["message"]


def test_live_health_endpoint() -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_health_endpoint() -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert "status" in response.json()
