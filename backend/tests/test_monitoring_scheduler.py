from __future__ import annotations

import tempfile
import threading
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.monitoring import MonitorEndpoint
from app.services.redis_queue import MonitoringQueue
from app.services.scheduler import MonitorScheduler


@pytest.fixture
def db_session() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )
    return session_factory


def test_due_monitor_discovery(db_session: sessionmaker[Session]) -> None:
    now = datetime.utcnow()
    with db_session() as session:
        session.add(
            MonitorEndpoint(
                url="http://example.com/ready",
                http_method="GET",
                expected_status_code=200,
                interval_seconds=30,
                timeout_seconds=5,
                active=True,
                next_check_at=now - timedelta(minutes=1),
            )
        )
        session.commit()

    scheduler = MonitorScheduler(session_factory=db_session, queue=None, batch_size=10)
    due = scheduler.find_due_monitors(now=now)
    assert len(due) == 1
    assert due[0].url == "http://example.com/ready"


def test_future_and_inactive_monitors_are_not_due(db_session: sessionmaker[Session]) -> None:
    now = datetime.utcnow()
    with db_session() as session:
        session.add_all(
            [
                MonitorEndpoint(
                    url="http://example.com/future",
                    http_method="GET",
                    expected_status_code=200,
                    interval_seconds=30,
                    timeout_seconds=5,
                    active=True,
                    next_check_at=now + timedelta(minutes=5),
                ),
                MonitorEndpoint(
                    url="http://example.com/inactive",
                    http_method="GET",
                    expected_status_code=200,
                    interval_seconds=30,
                    timeout_seconds=5,
                    active=False,
                    next_check_at=now - timedelta(minutes=5),
                ),
            ]
        )
        session.commit()

    scheduler = MonitorScheduler(session_factory=db_session, queue=None, batch_size=10)
    due = scheduler.find_due_monitors(now=now)
    assert due == []


def test_scheduler_claims_due_monitors_in_batches(db_session: sessionmaker[Session]) -> None:
    now = datetime.utcnow()
    with db_session() as session:
        session.add_all(
            [
                MonitorEndpoint(
                    url=f"http://example.com/{index}",
                    http_method="GET",
                    expected_status_code=200,
                    interval_seconds=30,
                    timeout_seconds=5,
                    active=True,
                    next_check_at=now - timedelta(minutes=index),
                )
                for index in range(1, 5)
            ]
        )
        session.commit()

    queue = MonitoringQueue()
    scheduler = MonitorScheduler(session_factory=db_session, queue=queue, batch_size=2)
    jobs = scheduler.claim_due_monitors(now=now)

    assert len(jobs) == 2
    assert queue.queue_depth() == 2
    assert {job.monitor_id for job in jobs} == {3, 4}


def test_two_schedulers_do_not_claim_the_same_monitor_concurrently() -> None:
    now = datetime.utcnow()
    with tempfile.NamedTemporaryFile(suffix=".sqlite3") as temp_db:
        engine = create_engine(
            f"sqlite:///{temp_db.name}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )

        with session_factory() as session:
            session.add_all(
                [
                    MonitorEndpoint(
                        url=f"http://example.com/concurrency/{index}",
                        http_method="GET",
                        expected_status_code=200,
                        interval_seconds=30,
                        timeout_seconds=5,
                        active=True,
                        next_check_at=now - timedelta(minutes=1),
                    )
                    for index in range(1, 11)
                ]
            )
            session.commit()

        barrier = threading.Barrier(2)
        results: list[list[object]] = []

        def claim_once() -> None:
            barrier.wait()
            scheduler = MonitorScheduler(session_factory=session_factory, queue=None, batch_size=10)
            results.append(scheduler.claim_due_monitors(now=now))

        first = threading.Thread(target=claim_once)
        second = threading.Thread(target=claim_once)
        first.start()
        second.start()
        first.join()
        second.join()

        claimed_ids = [job.monitor_id for jobs in results for job in jobs]
        assert len(claimed_ids) == len(set(claimed_ids)) == 10


def test_monitoring_queue_round_trip() -> None:
    queue = MonitoringQueue()
    job_id = queue.enqueue(
        {"monitor_id": 42, "url": "http://example.com/health", "status": "queued"}
    )
    retrieved = queue.dequeue()

    assert job_id == retrieved["job_id"]
    assert retrieved["status"] == "processing"
    queue.mark_processed(job_id)
    assert queue.metrics().jobs_processed == 1
