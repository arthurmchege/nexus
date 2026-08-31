from __future__ import annotations

from typing import Annotated

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
)

router = APIRouter(prefix="/monitors", tags=["monitors"])


def get_monitor_or_404(db: Session, monitor_id: int) -> MonitorEndpoint:
    endpoint = db.get(MonitorEndpoint, monitor_id)
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found.")
    return endpoint


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
    return endpoint


@router.get("", response_model=list[MonitorEndpointOut])
def list_monitors(
    active: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
) -> list[MonitorEndpoint]:
    statement = select(MonitorEndpoint)
    if active is not None:
        statement = statement.where(MonitorEndpoint.active.is_(active))
    statement = statement.order_by(MonitorEndpoint.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


@router.get("/{monitor_id}", response_model=MonitorEndpointOut)
def get_monitor(
    monitor_id: int,
    db: Session = Depends(get_db),
) -> MonitorEndpoint:
    return get_monitor_or_404(db, monitor_id)


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


@router.get("/{monitor_id}/history", response_model=list[MonitorResultOut])
def get_monitor_history(
    monitor_id: int,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
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
