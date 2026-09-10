from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class MonitorEndpoint(Base):
    """Registered HTTP endpoint and its scheduling state."""

    __tablename__ = "monitor_endpoints"
    __table_args__ = (
        UniqueConstraint("url", "http_method", name="uq_monitor_endpoint_url_method"),
        CheckConstraint("interval_seconds >= 10", name="ck_monitor_interval_min"),
        CheckConstraint("timeout_seconds >= 1", name="ck_monitor_timeout_min"),
        CheckConstraint("expected_status_code >= 100", name="ck_monitor_expected_status_min"),
        CheckConstraint("expected_status_code <= 599", name="ck_monitor_expected_status_max"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    http_method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET", index=True)
    expected_status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    health_state: Mapped[str] = mapped_column(String(16), nullable=False, default="up", index=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_successes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    recovery_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    notification_webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    next_check_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    last_check_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )
    claimed_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
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
    owner: Mapped[User] = relationship(back_populates="monitors")
    incidents: Mapped[list[Incident]] = relationship(
        back_populates="endpoint",
        cascade="all, delete-orphan",
    )


class MonitorResult(Base):
    """Persisted outcome of one monitoring check."""

    __tablename__ = "monitor_results"
    __table_args__ = (
        CheckConstraint("http_status >= 100", name="ck_monitor_result_status_min"),
        CheckConstraint("http_status <= 599", name="ck_monitor_result_status_max"),
        CheckConstraint("latency_ms >= 0", name="ck_monitor_result_latency_non_negative"),
        CheckConstraint("response_size >= 0", name="ck_monitor_result_response_size_non_negative"),
        Index("ix_monitor_results_endpoint_observed_at", "endpoint_id", "observed_at"),
        Index(
            "ix_monitor_results_partition_endpoint_observed",
            "partition_bucket",
            "endpoint_id",
            "observed_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_endpoints.id"), nullable=False, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    partition_bucket: Mapped[str] = mapped_column(
        String(7), nullable=False, default=lambda: datetime.utcnow().strftime("%Y-%m"), index=True
    )
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    response_size: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)

    endpoint: Mapped[MonitorEndpoint] = relationship(back_populates="results")


class Incident(Base):
    """A deduplicated health episode for one monitor."""

    __tablename__ = "incidents"
    __table_args__ = (
        Index(
            "uq_incidents_open_monitor",
            "monitor_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
        Index("ix_incidents_status_opened_at", "status", "opened_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    monitor_id: Mapped[int] = mapped_column(
        ForeignKey("monitor_endpoints.id"), nullable=False, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trigger_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)

    endpoint: Mapped[MonitorEndpoint] = relationship(back_populates="incidents")
    deliveries: Mapped[list[AlertDelivery]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )


class AlertDelivery(Base):
    """One idempotent notification attempt for an incident event."""

    __tablename__ = "alert_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "event",
            "channel",
            name="uq_alert_delivery_incident_event_channel",
        ),
        Index("ix_alert_deliveries_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    event: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    incident: Mapped[Incident] = relationship(back_populates="deliveries")
