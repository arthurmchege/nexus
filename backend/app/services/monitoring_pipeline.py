from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.monitoring import MonitoringCheckResult, MonitoringWorker, MonitorJob
from app.services.notifications import NotificationChannel
from app.services.redis_queue import MonitoringQueue
from app.services.result_writer import write_monitoring_result


def _monitor_job_from_payload(payload: dict[str, object]) -> MonitorJob:
    return MonitorJob(
        endpoint_id=int(payload["monitor_id"]),
        url=str(payload["url"]),
        method=str(payload.get("method", "GET")),
        expected_status_code=int(payload.get("expected_status_code", 200)),
        timeout_seconds=int(payload.get("timeout_seconds", 10)),
        allow_localhost=settings.app_env == "test",
        job_id=str(payload.get("job_id")) if payload.get("job_id") else None,
        scheduled_for=(
            datetime.fromisoformat(str(payload["scheduled_for"]))
            if payload.get("scheduled_for")
            else None
        ),
        attempt_number=int(payload.get("attempt_number", 0)),
        idempotency_key=(
            str(payload["idempotency_key"]) if payload.get("idempotency_key") else None
        ),
    )


async def process_queued_monitoring_job(
    queue: MonitoringQueue,
    *,
    session_factory: Callable[[], Session],
    notification_channel: NotificationChannel | None = None,
    max_retries: int = 2,
    retry_backoff_seconds: float = 0.5,
) -> MonitoringCheckResult | None:
    """Consume one queued job, persist its result, and evaluate alert state."""

    payload = queue.dequeue()
    if payload is None:
        return None

    job = _monitor_job_from_payload(payload)
    job.max_retries = max_retries
    job.retry_backoff_seconds = retry_backoff_seconds
    worker = MonitoringWorker(
        max_concurrency=1,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    try:
        result = await worker.run_job(job)
        with session_factory() as session:
            await write_monitoring_result(
                session,
                monitor_id=job.endpoint_id or 0,
                result=result,
                channel=notification_channel,
            )
        queue.mark_processed(str(payload["job_id"]))
        return result
    except Exception as exc:
        queue.mark_failed(str(payload["job_id"]), error=str(exc))
        raise


__all__ = ["process_queued_monitoring_job"]
