from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.monitoring import AlertDelivery, Incident, MonitorEndpoint
from app.services.monitoring import MonitoringCheckResult
from app.services.notifications import MockNotificationChannel
from app.services.result_writer import write_monitoring_result


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session


def failing_result() -> MonitoringCheckResult:
    return MonitoringCheckResult(
        endpoint_id=None,
        url="https://alerts.example.com/health",
        http_status=503,
        latency_ms=250,
        response_size=32,
        success=False,
        error_category="unexpected_status",
        error_details="Expected HTTP 200, received HTTP 503.",
    )


def successful_result() -> MonitoringCheckResult:
    return MonitoringCheckResult(
        endpoint_id=None,
        url="https://alerts.example.com/health",
        http_status=200,
        latency_ms=100,
        response_size=32,
        success=True,
    )


@pytest.mark.asyncio
async def test_result_write_opens_and_recovers_one_incident(
    db_session: Session,
) -> None:
    endpoint = MonitorEndpoint(
        url="https://alerts.example.com/health",
        http_method="GET",
        failure_threshold=2,
        recovery_threshold=2,
    )
    db_session.add(endpoint)
    db_session.commit()
    channel = MockNotificationChannel()
    start = datetime.utcnow()

    await write_monitoring_result(
        db_session,
        monitor_id=endpoint.id,
        result=failing_result(),
        observed_at=start,
        channel=channel,
    )
    await write_monitoring_result(
        db_session,
        monitor_id=endpoint.id,
        result=failing_result(),
        observed_at=start + timedelta(minutes=1),
        channel=channel,
    )
    await write_monitoring_result(
        db_session,
        monitor_id=endpoint.id,
        result=successful_result(),
        observed_at=start + timedelta(minutes=2),
        channel=channel,
    )
    await write_monitoring_result(
        db_session,
        monitor_id=endpoint.id,
        result=successful_result(),
        observed_at=start + timedelta(minutes=3),
        channel=channel,
    )

    assert db_session.query(Incident).count() == 1
    assert db_session.query(Incident).one().status == "resolved"
    assert db_session.query(AlertDelivery).count() == 2
    assert [message["event"] for message in channel.messages] == ["opened", "resolved"]


@pytest.mark.asyncio
async def test_flapping_does_not_create_notification_storm(db_session: Session) -> None:
    endpoint = MonitorEndpoint(
        url="https://flapping.example.com/health",
        http_method="GET",
        failure_threshold=3,
        recovery_threshold=2,
    )
    db_session.add(endpoint)
    db_session.commit()
    channel = MockNotificationChannel()
    start = datetime.utcnow()

    for index, result in enumerate(
        [
            failing_result(),
            failing_result(),
            failing_result(),
            successful_result(),
            failing_result(),
        ]
    ):
        await write_monitoring_result(
            db_session,
            monitor_id=endpoint.id,
            result=result,
            observed_at=start + timedelta(minutes=index),
            channel=channel,
        )

    assert db_session.query(Incident).count() == 1
    assert len(channel.messages) == 1
