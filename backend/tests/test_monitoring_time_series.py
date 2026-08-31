from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.monitoring import MonitorEndpoint, MonitorResult
from app.services.monitoring_queries import (
    compute_monitor_stats,
    compute_rollups,
    explain_monitor_result_query,
)
from app.services.time_series import build_latency_summary, partition_bucket_for


def test_partition_bucket_generation() -> None:
    bucket = partition_bucket_for(datetime(2026, 9, 15, 12, 30, 0))
    assert bucket == "2026-09"

    hourly = partition_bucket_for(datetime(2026, 9, 15, 12, 30, 0), bucket="hour")
    assert hourly == "2026-09-15T12:00"

    daily = partition_bucket_for(datetime(2026, 9, 15, 12, 30, 0), bucket="day")
    assert daily == "2026-09-15"


def test_latency_summary_computes_aggregates() -> None:
    summary = build_latency_summary(
        [
            {"latency_ms": 120},
            {"latency_ms": 200},
            {"latency_ms": 400},
            {"latency_ms": 1000},
        ]
    )

    assert summary["count"] == 4
    assert summary["avg_latency_ms"] == 430.0
    assert summary["p50_latency_ms"] == 400.0
    assert summary["p95_latency_ms"] == 1000.0
    assert summary["p99_latency_ms"] == 1000.0


def test_monitor_aggregation_across_partition_boundary() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )

    start = datetime(2026, 8, 31, 0, 0, 0)
    with session_factory() as session:
        endpoint = MonitorEndpoint(
            url="https://example.com/partition-test",
            http_method="GET",
            expected_status_code=200,
            interval_seconds=30,
            timeout_seconds=5,
            active=True,
            next_check_at=start,
        )
        session.add(endpoint)
        session.commit()
        session.refresh(endpoint)

        session.add_all(
            [
                MonitorResult(
                    endpoint_id=endpoint.id,
                    observed_at=datetime(2026, 8, 31, 23, 30, 0),
                    partition_bucket="2026-08",
                    http_status=200,
                    latency_ms=200,
                    response_size=256,
                    success=True,
                ),
                MonitorResult(
                    endpoint_id=endpoint.id,
                    observed_at=datetime(2026, 9, 1, 0, 5, 0),
                    partition_bucket="2026-09",
                    http_status=200,
                    latency_ms=400,
                    response_size=256,
                    success=True,
                ),
                MonitorResult(
                    endpoint_id=endpoint.id,
                    observed_at=datetime(2026, 9, 1, 1, 5, 0),
                    partition_bucket="2026-09",
                    http_status=500,
                    latency_ms=1000,
                    response_size=128,
                    success=False,
                ),
            ]
        )
        session.commit()

        stats = compute_monitor_stats(
            session,
            monitor_id=endpoint.id,
            start=datetime(2026, 8, 31),
            end=datetime(2026, 9, 2),
        )
        assert stats["total_checks"] == 3
        assert stats["successful_checks"] == 2
        assert stats["failed_checks"] == 1
        assert stats["uptime_percentage"] == 66.67
        assert stats["avg_latency_ms"] == 533.33

        rollups = compute_rollups(
            session,
            monitor_id=endpoint.id,
            bucket="day",
            start=datetime(2026, 8, 31),
            end=datetime(2026, 9, 2),
        )
        assert {item["bucket"] for item in rollups} == {"2026-08-31", "2026-09-01"}


def test_empty_window_returns_zeroed_aggregation() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )

    with session_factory() as session:
        endpoint = MonitorEndpoint(
            url="https://example.com/empty-window",
            http_method="GET",
            expected_status_code=200,
            interval_seconds=30,
            timeout_seconds=5,
            active=True,
            next_check_at=datetime.utcnow(),
        )
        session.add(endpoint)
        session.commit()
        session.refresh(endpoint)

        stats = compute_monitor_stats(
            session,
            monitor_id=endpoint.id,
            start=datetime(2026, 10, 1),
            end=datetime(2026, 10, 2),
        )
        assert stats["total_checks"] == 0
        assert stats["uptime_percentage"] == 0.0
        assert stats["avg_latency_ms"] == 0.0


def test_monitor_query_plan_uses_indexed_lookup() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )

    with session_factory() as session:
        endpoint = MonitorEndpoint(
            url="https://example.com/index-check",
            http_method="GET",
            expected_status_code=200,
            interval_seconds=30,
            timeout_seconds=5,
            active=True,
            next_check_at=datetime.utcnow(),
        )
        session.add(endpoint)
        session.commit()
        session.refresh(endpoint)

        session.add(
            MonitorResult(
                endpoint_id=endpoint.id,
                observed_at=datetime(2026, 11, 1, 6, 15, 0),
                partition_bucket="2026-11",
                http_status=200,
                latency_ms=150,
                response_size=128,
                success=True,
            )
        )
        session.commit()

        plan = explain_monitor_result_query(
            session,
            monitor_id=endpoint.id,
            start=datetime(2026, 11, 1),
            end=datetime(2026, 11, 2),
        )
        plan_text = "\n".join(str(row) for row in plan).lower()
        assert "monitor_results" in plan_text
