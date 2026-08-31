from fastapi import APIRouter

from app.core.redis_client import ping_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "nexus-backend"}


@router.get("/ready")
def health_ready() -> dict[str, str | bool]:
    redis_ok = ping_redis()
    return {"status": "ok" if redis_ok else "degraded", "redis": redis_ok}
