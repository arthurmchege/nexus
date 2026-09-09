from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.monitoring import Incident
from app.schemas.monitoring import IncidentOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    status: str | None = Query(default=None, pattern="^(open|resolved)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Incident]:
    statement = (
        select(Incident)
        .options(selectinload(Incident.deliveries))
        .order_by(Incident.opened_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status is not None:
        statement = statement.where(Incident.status == status)
    return list(db.scalars(statement).unique().all())
