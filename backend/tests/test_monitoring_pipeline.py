from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from test_monitoring_workers import mock_http_server

from app.db.base import Base
from app.models.monitoring import Incident, MonitorEndpoint, MonitorResult
from app.services.monitoring_pipeline import process_queued_monitoring_job
from app.services.notifications import MockNotificationChannel
from app.services.redis_queue import MonitoringQueue
from app.services.scheduler import MonitorScheduler


@pytest.fixture
def session_factory(tmp_path) -> Generator[sessionmaker[Session], None, None]:  # type: ignore[no-untyped-def]
    engine = create_engine(f"sqlite:///{tmp_path / 'pipeline.db'}")
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@pytest.mark.asyncio
async def test_scheduler_queue_worker_writes_result_and_opens_incident(
    session_factory: sessionmaker[Session],
) -> None:
    with mock_http_server(status_code=503) as monitor_url:
        with session_factory() as session:
            endpoint = MonitorEndpoint(
                url=monitor_url,
                http_method="GET",
                expected_status_code=200,
                failure_threshold=1,
                recovery_threshold=1,
            )
            session.add(endpoint)
            session.commit()
            monitor_id = endpoint.id

        queue = MonitoringQueue()
        scheduler = MonitorScheduler(session_factory, queue=queue, batch_size=1)
        claimed = scheduler.claim_due_monitors(limit=1)
        channel = MockNotificationChannel()

        result = await process_queued_monitoring_job(
            queue,
            session_factory=session_factory,
            notification_channel=channel,
            max_retries=0,
        )

        assert claimed[0].monitor_id == monitor_id
        assert result is not None
        assert result.success is False

    with session_factory() as session:
        assert session.query(MonitorResult).filter_by(endpoint_id=monitor_id).count() == 1
        incident = session.query(Incident).filter_by(monitor_id=monitor_id).one()
        assert incident.status == "open"
        assert len(channel.messages) == 1
        assert channel.messages[0]["event"] == "opened"
