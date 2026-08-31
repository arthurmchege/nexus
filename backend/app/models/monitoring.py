from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MonitorEndpoint(Base):
    __tablename__ = "monitor_endpoints"
    __table_args__ = (
        UniqueConstraint("url", "http_method", name="uq_monitor_endpoint_url_method"),
        CheckConstraint("interval_seconds >= 10", name="ck_monitor_interval_min"),
        CheckConstraint("timeout_seconds >= 1", name="ck_monitor_timeout_min"),
        CheckConstraint(
            "expected_status_code >= 100", name="ck_monitor_expected_status_min"
        ),
        CheckConstraint(
            "expected_status_code <= 599", name="ck_monitor_expected_status_max"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    http_method: Mapped[str] = mapped_column(
        String(10), nullable=False, default="GET", index=True
    )
    expected_status_code: Mapped[int] = mapped_column(
        Integer, nullable=False, default=200
    )
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    results: Mapped[list[MonitorResult]] = relationship(
        back_populates="endpoint",
        cascade="all, delete-orphan",
    )


class MonitorResult(Base):
    __tablename__ = "monitor_results"
    __table_args__ = (
        CheckConstraint("http_status >= 100", name="ck_monitor_result_status_min"),
        CheckConstraint("http_status <= 599", name="ck_monitor_result_status_max"),
        CheckConstraint(
            "latency_ms >= 0", name="ck_monitor_result_latency_non_negative"
        ),
        CheckConstraint(
            "response_size >= 0", name="ck_monitor_result_response_size_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_endpoints.id"), nullable=False, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    response_size: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    error_category: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    endpoint: Mapped[MonitorEndpoint] = relationship(back_populates="results")
