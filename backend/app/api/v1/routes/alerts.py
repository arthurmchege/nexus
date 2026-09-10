from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.monitoring import Incident, MonitorEndpoint
from app.models.user import User
from app.schemas.monitoring import IncidentOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    status: str | None = Query(default=None, pattern="^(open|resolved)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Incident]:
    statement = (
        select(Incident)
        .join(Incident.endpoint)
        .where(MonitorEndpoint.owner_id == user.id)
        .options(selectinload(Incident.deliveries))
        .order_by(Incident.opened_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status is not None:
        statement = statement.where(Incident.status == status)
    return list(db.scalars(statement).unique().all())
