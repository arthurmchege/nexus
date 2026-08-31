from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.services.monitoring import validate_monitor_url


class MonitorEndpointBase(BaseModel):
    url: str = Field(..., max_length=2048)
    http_method: str = Field(default="GET", min_length=1, max_length=10)
    expected_status_code: int = Field(default=200, ge=100, le=599)
    interval_seconds: int = Field(default=60, ge=10)
    timeout_seconds: int = Field(default=10, ge=1)
    active: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        try:
            validate_monitor_url(value, allow_localhost=settings.app_env == "test")
        except ValueError as exc:  # pragma: no cover - validation layer
            raise ValueError(str(exc)) from exc
        return value

    @field_validator("http_method")
    @classmethod
    def validate_http_method(cls, value: str) -> str:
        method = value.upper()
        allowed = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        if method not in allowed:
            raise ValueError("Unsupported HTTP method.")
        return method


class MonitorEndpointCreate(MonitorEndpointBase):
    pass


class MonitorEndpointUpdate(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    http_method: str | None = Field(default=None, min_length=1, max_length=10)
    expected_status_code: int | None = Field(default=None, ge=100, le=599)
    interval_seconds: int | None = Field(default=None, ge=10)
    timeout_seconds: int | None = Field(default=None, ge=1)
    active: bool | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            validate_monitor_url(value, allow_localhost=settings.app_env == "test")
        except ValueError as exc:  # pragma: no cover - validation layer
            raise ValueError(str(exc)) from exc
        return value

    @field_validator("http_method")
    @classmethod
    def validate_http_method(cls, value: str | None) -> str | None:
        if value is None:
            return value
        method = value.upper()
        allowed = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        if method not in allowed:
            raise ValueError("Unsupported HTTP method.")
        return method


class MonitorEndpointOut(MonitorEndpointBase):
    id: int
    created_at: datetime
    updated_at: datetime
    status: str = "unknown"

    model_config = ConfigDict(from_attributes=True)


class MonitorStatsOut(BaseModel):
    monitor_id: int
    window_start: datetime
    window_end: datetime
    total_checks: int
    successful_checks: int
    failed_checks: int
    uptime_percentage: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    hourly_rollups: list[dict[str, int | float | str]] = Field(default_factory=list)
    daily_rollups: list[dict[str, int | float | str]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MonitorResultOut(BaseModel):
    id: int
    endpoint_id: int
    observed_at: datetime
    http_status: int
    latency_ms: int
    response_size: int
    success: bool
    error_category: str | None = None
    error_details: str | None = None

    model_config = ConfigDict(from_attributes=True)
