import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alembic import command
from alembic.config import Config
from app.api.router import api_router
from app.core.config import BACKEND_DIR, settings
from app.core.logging import logger

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="NEXUS foundation project scaffold",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": f"{settings.app_name} API is running"}


@app.middleware("http")
async def request_logging_middleware(request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "HTTP request completed",
        extra={
            "event": "http_request_completed",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


def run_database_migrations() -> None:
    if settings.app_env in {"production", "test"}:
        return

    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


@app.on_event("startup")
def startup_event() -> None:
    run_database_migrations()
    logger.info("NEXUS backend startup complete")
