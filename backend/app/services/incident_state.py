from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.monitoring import Incident, MonitorEndpoint


@dataclass(frozen=True, slots=True)
class StateTransition:
    monitor_id: int
    previous_state: str
    current_state: str
    incident: Incident | None = None
    event: str | None = None


def evaluate_monitor_state(
    session: Session,
    *,
    monitor_id: int,
    success: bool,
    observed_at: datetime,
    trigger_reason: str | None = None,
) -> StateTransition:
    """Apply one result to a monitor's threshold-based health state."""

    statement = select(MonitorEndpoint).where(MonitorEndpoint.id == monitor_id)
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        statement = statement.with_for_update()
    endpoint = session.scalar(statement)
    if endpoint is None:
        raise ValueError(f"Monitor {monitor_id} does not exist.")

    previous_state = endpoint.health_state
    if success:
        endpoint.consecutive_successes += 1
        endpoint.consecutive_failures = 0
        if (
            endpoint.health_state == "down"
            and endpoint.consecutive_successes >= endpoint.recovery_threshold
        ):
            endpoint.health_state = "up"
            endpoint.consecutive_successes = 0
            incident = session.scalar(
                select(Incident)
                .where(Incident.monitor_id == monitor_id, Incident.status == "open")
                .order_by(Incident.opened_at.desc())
                .limit(1)
            )
            if incident is not None:
                incident.status = "resolved"
                incident.resolved_at = observed_at
            return StateTransition(
                monitor_id=monitor_id,
                previous_state=previous_state,
                current_state=endpoint.health_state,
                incident=incident,
                event="resolved" if incident is not None else None,
            )
    else:
        endpoint.consecutive_failures += 1
        endpoint.consecutive_successes = 0
        if (
            endpoint.health_state == "up"
            and endpoint.consecutive_failures >= endpoint.failure_threshold
        ):
            endpoint.health_state = "down"
            endpoint.consecutive_failures = 0
            incident = Incident(
                monitor_id=monitor_id,
                opened_at=observed_at,
                trigger_reason=trigger_reason or "consecutive monitor failures",
                status="open",
            )
            session.add(incident)
            return StateTransition(
                monitor_id=monitor_id,
                previous_state=previous_state,
                current_state=endpoint.health_state,
                incident=incident,
                event="opened",
            )

    return StateTransition(
        monitor_id=monitor_id,
        previous_state=previous_state,
        current_state=endpoint.health_state,
    )


__all__ = ["StateTransition", "evaluate_monitor_state"]
