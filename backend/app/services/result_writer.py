from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.monitoring import MonitorEndpoint, MonitorResult
from app.services.incident_state import StateTransition, evaluate_monitor_state
from app.services.monitoring import MonitoringCheckResult
from app.services.notifications import NotificationChannel, WebhookChannel, dispatch_alert
from app.services.time_series import partition_bucket_for


async def write_monitoring_result(
    session: Session,
    *,
    monitor_id: int,
    result: MonitoringCheckResult,
    observed_at: datetime | None = None,
    channel: NotificationChannel | None = None,
) -> tuple[MonitorResult, StateTransition]:
    """Persist a check, evaluate health, and dispatch any state transition."""

    endpoint = session.get(MonitorEndpoint, monitor_id)
    if endpoint is None:
        raise ValueError(f"Monitor {monitor_id} does not exist.")

    timestamp = observed_at or datetime.utcnow()
    stored_result = MonitorResult(
        endpoint_id=monitor_id,
        observed_at=timestamp,
        partition_bucket=partition_bucket_for(timestamp),
        http_status=result.http_status or 599,
        latency_ms=result.latency_ms,
        response_size=result.response_size,
        success=result.success,
        error_category=result.error_category,
        error_details=result.error_details,
    )
    session.add(stored_result)
    session.flush()
    transition = evaluate_monitor_state(
        session,
        monitor_id=monitor_id,
        success=result.success,
        observed_at=timestamp,
        trigger_reason=result.error_details or result.error_category,
    )
    session.commit()

    if transition.event and transition.incident is not None:
        delivery_channel = channel
        if delivery_channel is None and endpoint.notification_webhook_url:
            delivery_channel = WebhookChannel(endpoint.notification_webhook_url)
        if delivery_channel is not None:
            await dispatch_alert(
                session,
                incident=transition.incident,
                event=transition.event,
                channel=delivery_channel,
                channel_name=(
                    "webhook" if isinstance(delivery_channel, WebhookChannel) else "mock"
                ),
            )

    return stored_result, transition


__all__ = ["write_monitoring_result"]
