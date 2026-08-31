from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import logger

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="NEXUS foundation project scaffold",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": f"{settings.app_name} API is running"}


@app.on_event("startup")
def startup_event() -> None:
    logger.info("NEXUS backend startup complete")
