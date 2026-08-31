from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.monitoring import MonitorEndpoint


@dataclass(slots=True)
class ScheduledMonitorJob:
    monitor_id: int
    url: str
    method: str
    expected_status_code: int
    timeout_seconds: int
    interval_seconds: int
    scheduled_for: datetime
    attempt_number: int = 0
    job_id: str | None = None
    idempotency_key: str | None = None


class MonitorScheduler:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        queue: Any | None = None,
        *,
        batch_size: int = 100,
    ) -> None:
        self.session_factory = session_factory
        self.queue = queue
        self.batch_size = max(1, batch_size)

    def find_due_monitors(
        self,
        *,
        now: datetime | None = None,
        limit: int | None = None,
    ) -> list[MonitorEndpoint]:
        current_time = now or datetime.utcnow()
        statement = (
            select(MonitorEndpoint)
            .where(MonitorEndpoint.active.is_(True))
            .where(MonitorEndpoint.next_check_at <= current_time)
            .order_by(MonitorEndpoint.next_check_at.asc())
            .limit(limit or self.batch_size)
        )
        with self.session_factory() as session:
            return list(session.scalars(statement).all())

    def claim_due_monitors(
        self,
        *,
        now: datetime | None = None,
        limit: int | None = None,
    ) -> list[ScheduledMonitorJob]:
        current_time = now or datetime.utcnow()
        batch_limit = min(limit or self.batch_size, self.batch_size)
        claimed: list[ScheduledMonitorJob] = []
        claim_token = f"scheduler:{uuid.uuid4()}"

        with self.session_factory() as session:
            bind = session.bind
            dialect_name = bind.dialect.name if bind is not None else "sqlite"

            if dialect_name == "postgresql":
                statement = (
                    select(MonitorEndpoint)
                    .where(MonitorEndpoint.active.is_(True))
                    .where(MonitorEndpoint.next_check_at <= current_time)
                    .where(MonitorEndpoint.claimed_at.is_(None))
                    .order_by(MonitorEndpoint.next_check_at.asc())
                    .limit(batch_limit)
                    .with_for_update(skip_locked=True)
                )
            else:
                statement = (
                    select(MonitorEndpoint)
                    .where(MonitorEndpoint.active.is_(True))
                    .where(MonitorEndpoint.next_check_at <= current_time)
                    .where(MonitorEndpoint.claimed_at.is_(None))
                    .order_by(MonitorEndpoint.next_check_at.asc())
                    .limit(batch_limit)
                )
                session.execute(text("BEGIN IMMEDIATE"))

            endpoints = list(session.scalars(statement).all())

            for endpoint in endpoints:
                endpoint.last_check_at = current_time
                endpoint.claimed_at = current_time
                endpoint.claimed_by = claim_token
                endpoint.next_check_at = current_time + timedelta(seconds=endpoint.interval_seconds)
                job = ScheduledMonitorJob(
                    monitor_id=endpoint.id,
                    url=endpoint.url,
                    method=endpoint.http_method,
                    expected_status_code=endpoint.expected_status_code,
                    timeout_seconds=endpoint.timeout_seconds,
                    interval_seconds=endpoint.interval_seconds,
                    scheduled_for=current_time,
                    attempt_number=0,
                    job_id=f"{endpoint.id}:{current_time.isoformat(timespec='seconds')}",
                    idempotency_key=f"monitor:{endpoint.id}:scheduled:{current_time.isoformat(timespec='seconds')}",
                )
                claimed.append(job)

            session.commit()

        if self.queue is not None:
            for job in claimed:
                self.queue.enqueue(job)

        return claimed


__all__ = ["MonitorScheduler", "ScheduledMonitorJob"]
