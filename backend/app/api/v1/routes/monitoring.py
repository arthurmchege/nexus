from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.monitoring import MonitorEndpoint, MonitorResult
from app.schemas.monitoring import (
    MonitorEndpointCreate,
    MonitorEndpointOut,
    MonitorEndpointUpdate,
    MonitorResultOut,
    MonitorStatsOut,
)
from app.services.monitoring_queries import compute_monitor_stats, compute_rollups

router = APIRouter(prefix="/monitors", tags=["monitors"])


def get_monitor_or_404(db: Session, monitor_id: int) -> MonitorEndpoint:
    endpoint = db.get(MonitorEndpoint, monitor_id)
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found.")
    return endpoint


def get_monitor_status(db: Session, monitor_id: int) -> str:
    latest_result = db.scalar(
        select(MonitorResult)
        .where(MonitorResult.endpoint_id == monitor_id)
        .order_by(MonitorResult.observed_at.desc())
        .limit(1)
    )
    if latest_result is None:
        return "unknown"
    return "up" if latest_result.success else "down"


@router.post("", response_model=MonitorEndpointOut, status_code=status.HTTP_201_CREATED)
def create_monitor(
    payload: MonitorEndpointCreate,
    db: Session = Depends(get_db),
) -> MonitorEndpoint:
    endpoint = MonitorEndpoint(
        url=payload.url,
        http_method=payload.http_method,
        expected_status_code=payload.expected_status_code,
        interval_seconds=payload.interval_seconds,
        timeout_seconds=payload.timeout_seconds,
        active=payload.active,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    endpoint.status = "unknown"
    return endpoint


@router.get("", response_model=list[MonitorEndpointOut])
def list_monitors(
    active: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[MonitorEndpoint]:
    statement = select(MonitorEndpoint)
    if active is not None:
        statement = statement.where(MonitorEndpoint.active.is_(active))
    statement = statement.order_by(MonitorEndpoint.created_at.desc()).offset(skip).limit(limit)
    endpoints = list(db.scalars(statement).all())
    for endpoint in endpoints:
        endpoint.status = get_monitor_status(db, endpoint.id)
    return endpoints


@router.get("/summary")
def get_system_summary(
    window_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    end = datetime.utcnow()
    start = end - timedelta(days=window_days)
    endpoints = list(db.scalars(select(MonitorEndpoint)).all())
    total_monitors = len(endpoints)
    down_monitors = 0
    total_checks = 0
    successful_checks = 0

    for endpoint in endpoints:
        if get_monitor_status(db, endpoint.id) == "down":
            down_monitors += 1

        stats = compute_monitor_stats(db, monitor_id=endpoint.id, start=start, end=end)
        total_checks += stats["total_checks"]
        successful_checks += stats["successful_checks"]

    uptime_percentage = 0.0
    if total_checks:
        uptime_percentage = round((successful_checks / total_checks) * 100, 2)

    return {
        "total_monitors": total_monitors,
        "down_monitors": down_monitors,
        "overall_uptime_percentage": uptime_percentage,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
    }


@router.get("/{monitor_id}", response_model=MonitorEndpointOut)
def get_monitor(
    monitor_id: int,
    db: Session = Depends(get_db),
) -> MonitorEndpoint:
    endpoint = get_monitor_or_404(db, monitor_id)
    endpoint.status = get_monitor_status(db, monitor_id)
    return endpoint


@router.patch("/{monitor_id}", response_model=MonitorEndpointOut)
def update_monitor(
    monitor_id: int,
    payload: MonitorEndpointUpdate,
    db: Session = Depends(get_db),
) -> MonitorEndpoint:
    endpoint = get_monitor_or_404(db, monitor_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(endpoint, field_name, value)
    db.commit()
    db.refresh(endpoint)
    endpoint.status = get_monitor_status(db, monitor_id)
    return endpoint


@router.post("/{monitor_id}/activate", response_model=MonitorEndpointOut)
def activate_monitor(
    monitor_id: int,
    db: Session = Depends(get_db),
) -> MonitorEndpoint:
    endpoint = get_monitor_or_404(db, monitor_id)
    endpoint.active = True
    db.commit()
    db.refresh(endpoint)
    endpoint.status = get_monitor_status(db, monitor_id)
    return endpoint


@router.post("/{monitor_id}/deactivate", response_model=MonitorEndpointOut)
def deactivate_monitor(
    monitor_id: int,
    db: Session = Depends(get_db),
) -> MonitorEndpoint:
    endpoint = get_monitor_or_404(db, monitor_id)
    endpoint.active = False
    db.commit()
    db.refresh(endpoint)
    endpoint.status = get_monitor_status(db, monitor_id)
    return endpoint


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_monitor(
    monitor_id: int,
    db: Session = Depends(get_db),
) -> Response:
    endpoint = get_monitor_or_404(db, monitor_id)
    db.delete(endpoint)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{monitor_id}/stats", response_model=MonitorStatsOut)
def get_monitor_stats(
    monitor_id: int,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    window_days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    get_monitor_or_404(db, monitor_id)
    if start and end and start >= end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="start must be earlier than end."
        )

    if start is None and end is None:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=window_days)
    elif start is None:
        start_time = end - timedelta(days=window_days)
        end_time = end
    elif end is None:
        end_time = datetime.utcnow()
        start_time = start
    else:
        start_time = start
        end_time = end

    stats = compute_monitor_stats(db, monitor_id=monitor_id, start=start_time, end=end_time)
    hourly_rollups = compute_rollups(
        db, monitor_id=monitor_id, bucket="hour", start=start_time, end=end_time
    )
    daily_rollups = compute_rollups(
        db, monitor_id=monitor_id, bucket="day", start=start_time, end=end_time
    )
    return {
        "monitor_id": monitor_id,
        "window_start": start_time,
        "window_end": end_time,
        "total_checks": stats["total_checks"],
        "successful_checks": stats["successful_checks"],
        "failed_checks": stats["failed_checks"],
        "uptime_percentage": stats["uptime_percentage"],
        "avg_latency_ms": stats["avg_latency_ms"],
        "p50_latency_ms": stats["p50_latency_ms"],
        "p95_latency_ms": stats["p95_latency_ms"],
        "p99_latency_ms": stats["p99_latency_ms"],
        "hourly_rollups": hourly_rollups,
        "daily_rollups": daily_rollups,
    }


@router.get("/{monitor_id}/history", response_model=list[MonitorResultOut])
def get_monitor_history(
    monitor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[MonitorResult]:
    get_monitor_or_404(db, monitor_id)
    statement = (
        select(MonitorResult)
        .where(MonitorResult.endpoint_id == monitor_id)
        .order_by(MonitorResult.observed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())
