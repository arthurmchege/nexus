from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.redis_client import ping_redis, redis_client
from app.db.session import get_db
from app.models.monitoring import MonitorEndpoint, MonitorResult

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "nexus-backend"}


@router.get("/ready")
def health_ready() -> dict[str, str | bool]:
    redis_ok = ping_redis()
    return {"status": "ok" if redis_ok else "degraded", "redis": redis_ok}


@router.get("/metrics")
def health_metrics(db: Session = Depends(get_db)) -> dict[str, Any]:
    redis_ok = ping_redis()
    queue_depth = 0
    worker_heartbeat = False
    if redis_ok:
        queue_depth = int(redis_client.llen("nexus:monitoring:jobs"))
        worker_heartbeat = bool(redis_client.exists("nexus:worker:heartbeat"))

    recent_results = list(
        db.scalars(
            select(MonitorResult).order_by(MonitorResult.observed_at.desc()).limit(100)
        ).all()
    )
    success_rate = (
        round(sum(result.success for result in recent_results) / len(recent_results) * 100, 2)
        if recent_results
        else None
    )
    return {
        "redis": {"ok": redis_ok},
        "queue": {"depth": queue_depth},
        "monitors": {
            "active": db.scalar(
                select(func.count())
                .select_from(MonitorEndpoint)
                .where(MonitorEndpoint.active.is_(True))
            )
        },
        "worker": {"heartbeat": worker_heartbeat},
        "checks": {
            "recent_success_rate_percentage": success_rate,
            "sample_size": len(recent_results),
        },
    }
