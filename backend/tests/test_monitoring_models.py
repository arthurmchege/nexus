from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.monitoring import MonitorEndpoint, MonitorResult


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session


def test_monitor_endpoint_create(db_session: Session) -> None:
    endpoint = MonitorEndpoint(
        url="https://example.com/health",
        http_method="GET",
        expected_status_code=200,
        interval_seconds=30,
        timeout_seconds=5,
        active=True,
    )

    db_session.add(endpoint)
    db_session.commit()

    stored = db_session.scalar(
        select(MonitorEndpoint).where(
            MonitorEndpoint.url == "https://example.com/health"
        )
    )
    assert stored is not None
    assert stored.http_method == "GET"
    assert stored.expected_status_code == 200
    assert stored.active is True
    assert isinstance(stored.created_at, datetime)
    assert isinstance(stored.updated_at, datetime)


def test_monitor_endpoint_unique_url_method_constraint(db_session: Session) -> None:
    endpoint_one = MonitorEndpoint(url="https://example.com/health", http_method="GET")
    endpoint_two = MonitorEndpoint(url="https://example.com/health", http_method="GET")

    db_session.add(endpoint_one)
    db_session.commit()

    db_session.add(endpoint_two)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_monitor_result_requires_endpoint(db_session: Session) -> None:
    result = MonitorResult(
        endpoint_id=999,
        observed_at=datetime.utcnow(),
        http_status=500,
        latency_ms=125,
        response_size=512,
        success=False,
        error_category="http_error",
        error_details="server responded 500",
    )

    db_session.add(result)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_monitor_result_can_attach_to_endpoint(db_session: Session) -> None:
    endpoint = MonitorEndpoint(url="https://example.com/api", http_method="GET")
    db_session.add(endpoint)
    db_session.commit()

    result = MonitorResult(
        endpoint_id=endpoint.id,
        observed_at=datetime.utcnow(),
        http_status=200,
        latency_ms=50,
        response_size=128,
        success=True,
        error_category=None,
        error_details=None,
    )
    db_session.add(result)
    db_session.commit()

    stored = db_session.scalar(
        select(MonitorResult).where(MonitorResult.endpoint_id == endpoint.id)
    )
    assert stored is not None
    assert stored.success is True
    assert stored.http_status == 200
