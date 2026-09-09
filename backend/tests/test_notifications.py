from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.monitoring import AlertDelivery, Incident, MonitorEndpoint
from app.services.notifications import MockNotificationChannel, dispatch_alert


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session


def make_incident(db_session: Session, suffix: str) -> Incident:
    endpoint = MonitorEndpoint(url=f"https://{suffix}.example.com/health", http_method="GET")
    db_session.add(endpoint)
    db_session.flush()
    incident = Incident(
        monitor_id=endpoint.id,
        opened_at=datetime.utcnow(),
        trigger_reason="HTTP 503",
        status="open",
    )
    db_session.add(incident)
    db_session.commit()
    return incident


@pytest.mark.asyncio
async def test_dispatches_open_and_resolve_events(db_session: Session) -> None:
    incident = make_incident(db_session, "open")
    channel = MockNotificationChannel()

    opened = await dispatch_alert(
        db_session,
        incident=incident,
        event="opened",
        channel=channel,
    )
    incident.status = "resolved"
    incident.resolved_at = datetime.utcnow()
    db_session.commit()
    resolved = await dispatch_alert(
        db_session,
        incident=incident,
        event="resolved",
        channel=channel,
    )

    assert opened.status == "delivered"
    assert resolved.status == "delivered"
    assert [message["event"] for message in channel.messages] == ["opened", "resolved"]


@pytest.mark.asyncio
async def test_dispatch_deduplicates_same_incident_event(db_session: Session) -> None:
    incident = make_incident(db_session, "dedup")
    channel = MockNotificationChannel()

    first = await dispatch_alert(db_session, incident=incident, event="opened", channel=channel)
    second = await dispatch_alert(db_session, incident=incident, event="opened", channel=channel)

    assert first.id == second.id
    assert len(channel.messages) == 1
    assert db_session.query(AlertDelivery).count() == 1


@pytest.mark.asyncio
async def test_failed_channel_retries_then_gives_up(db_session: Session) -> None:
    incident = make_incident(db_session, "failure")

    class FailingChannel:
        attempts = 0

        async def send(self, payload: dict[str, object]) -> None:
            self.attempts += 1
            raise RuntimeError("webhook unavailable")

    channel = FailingChannel()
    delivery = await dispatch_alert(
        db_session,
        incident=incident,
        event="opened",
        channel=channel,
        max_attempts=3,
        backoff_seconds=0,
    )

    assert channel.attempts == 3
    assert delivery.status == "failed"
    assert delivery.attempts == 3
    assert delivery.last_error == "webhook unavailable"


@pytest.mark.asyncio
async def test_monitors_have_independent_delivery_records(db_session: Session) -> None:
    first_incident = make_incident(db_session, "first")
    second_incident = make_incident(db_session, "second")
    channel = MockNotificationChannel()

    await dispatch_alert(db_session, incident=first_incident, event="opened", channel=channel)
    await dispatch_alert(db_session, incident=second_incident, event="opened", channel=channel)

    assert [message["incident_id"] for message in channel.messages] == [
        first_incident.id,
        second_incident.id,
    ]
