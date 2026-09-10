from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.monitoring import AlertDelivery, Incident


class NotificationChannel(Protocol):
    async def send(self, payload: Mapping[str, object]) -> None: ...


class WebhookChannel:
    """Deliver alert events to an HTTP webhook."""

    def __init__(self, url: str, *, timeout_seconds: float = 10.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds

    async def send(self, payload: Mapping[str, object]) -> None:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.url, json=dict(payload))
            response.raise_for_status()


class MockNotificationChannel:
    """Collect alert events for tests and local verification."""

    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send(self, payload: Mapping[str, object]) -> None:
        self.messages.append(dict(payload))


async def dispatch_alert(
    session: Session,
    *,
    incident: Incident,
    event: str,
    channel: NotificationChannel,
    channel_name: str = "mock",
    max_attempts: int = 3,
    backoff_seconds: float = 0.1,
) -> AlertDelivery:
    """Send one deduplicated incident event with bounded retry."""

    delivery = session.scalar(
        select(AlertDelivery).where(
            AlertDelivery.incident_id == incident.id,
            AlertDelivery.event == event,
            AlertDelivery.channel == channel_name,
        )
    )
    if delivery is None:
        delivery = AlertDelivery(
            incident_id=incident.id,
            event=event,
            channel=channel_name,
            status="pending",
        )
        try:
            with session.begin_nested():
                session.add(delivery)
                session.flush()
        except IntegrityError:
            delivery = session.scalar(
                select(AlertDelivery).where(
                    AlertDelivery.incident_id == incident.id,
                    AlertDelivery.event == event,
                    AlertDelivery.channel == channel_name,
                )
            )
            if delivery is None:
                raise

    if delivery.status == "delivered":
        return delivery

    payload = {
        "incident_id": incident.id,
        "monitor_id": incident.monitor_id,
        "event": event,
        "status": incident.status,
        "trigger_reason": incident.trigger_reason,
        "occurred_at": (
            (incident.opened_at if event == "opened" else incident.resolved_at).isoformat()
            if (incident.opened_at if event == "opened" else incident.resolved_at)
            else datetime.utcnow().isoformat()
        ),
    }
    for attempt in range(delivery.attempts + 1, max_attempts + 1):
        delivery.attempts = attempt
        try:
            await channel.send(payload)
        except Exception as exc:
            delivery.last_error = str(exc)
            delivery.status = "failed" if attempt == max_attempts else "pending"
            if attempt < max_attempts:
                await asyncio.sleep(backoff_seconds * (2 ** (attempt - 1)))
            continue
        delivery.status = "delivered"
        delivery.delivered_at = datetime.utcnow()
        delivery.last_error = None
        break

    session.commit()
    return delivery


__all__ = [
    "MockNotificationChannel",
    "NotificationChannel",
    "WebhookChannel",
    "dispatch_alert",
]
