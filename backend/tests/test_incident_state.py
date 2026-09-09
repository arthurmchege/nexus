from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.monitoring import Incident, MonitorEndpoint
from app.services.incident_state import evaluate_monitor_state


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session


def make_monitor(db_session: Session, **overrides: int | str) -> MonitorEndpoint:
    endpoint = MonitorEndpoint(
        url="https://alerts.example.com/health", http_method="GET", **overrides
    )
    db_session.add(endpoint)
    db_session.commit()
    return endpoint


def test_threshold_crossing_opens_one_incident(db_session: Session) -> None:
    endpoint = make_monitor(db_session)
    observed_at = datetime.utcnow()

    first = evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=False,
        observed_at=observed_at,
        trigger_reason="HTTP 503",
    )
    second = evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=False,
        observed_at=observed_at + timedelta(seconds=60),
        trigger_reason="HTTP 503",
    )
    db_session.commit()

    assert first.event is None
    assert second.event == "opened"
    assert db_session.query(Incident).filter_by(monitor_id=endpoint.id, status="open").count() == 1


def test_single_failure_does_not_open_incident(db_session: Session) -> None:
    endpoint = make_monitor(db_session)

    transition = evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=False,
        observed_at=datetime.utcnow(),
    )
    db_session.commit()

    assert transition.current_state == "degraded"
    assert transition.incident is None
    assert db_session.query(Incident).count() == 0


def test_recovery_requires_threshold_and_resolves_incident(db_session: Session) -> None:
    endpoint = make_monitor(db_session)
    opened_at = datetime.utcnow()
    evaluate_monitor_state(db_session, monitor_id=endpoint.id, success=False, observed_at=opened_at)
    evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=False,
        observed_at=opened_at + timedelta(seconds=60),
    )
    db_session.commit()

    first_success = evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=True,
        observed_at=opened_at + timedelta(seconds=120),
    )
    assert first_success.event is None
    second_success = evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=True,
        observed_at=opened_at + timedelta(seconds=180),
    )
    db_session.commit()

    assert second_success.event == "resolved"
    incident = db_session.query(Incident).one()
    assert incident.status == "resolved"
    assert incident.resolved_at == opened_at + timedelta(seconds=180)


def test_flapping_does_not_duplicate_open_incident(db_session: Session) -> None:
    endpoint = make_monitor(db_session, failure_threshold=3, recovery_threshold=2)
    observed_at = datetime.utcnow()
    for offset in (0, 60, 120):
        evaluate_monitor_state(
            db_session,
            monitor_id=endpoint.id,
            success=False,
            observed_at=observed_at + timedelta(seconds=offset),
        )
    evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=True,
        observed_at=observed_at + timedelta(seconds=180),
    )
    evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=False,
        observed_at=observed_at + timedelta(seconds=240),
    )
    evaluate_monitor_state(
        db_session,
        monitor_id=endpoint.id,
        success=False,
        observed_at=observed_at + timedelta(seconds=300),
    )
    db_session.commit()

    assert db_session.query(Incident).filter_by(monitor_id=endpoint.id).count() == 1
    assert db_session.query(Incident).filter_by(status="open").count() == 1
