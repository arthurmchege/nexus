from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.monitoring import MonitorResult
from app.services.time_series import build_latency_summary, partition_bucket_for


def fetch_monitor_results(
    db: Session,
    *,
    monitor_id: int,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[MonitorResult]:
    statement = select(MonitorResult).where(MonitorResult.endpoint_id == monitor_id)
    if start is not None:
        statement = statement.where(MonitorResult.observed_at >= start)
    if end is not None:
        statement = statement.where(MonitorResult.observed_at < end)
    statement = statement.order_by(MonitorResult.observed_at.asc())
    return list(db.scalars(statement).all())


def explain_monitor_result_query(
    db: Session,
    *,
    monitor_id: int,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[tuple[str, ...]]:
    statement = (
        select(MonitorResult.id)
        .where(MonitorResult.endpoint_id == monitor_id)
        .where(MonitorResult.observed_at >= (start or datetime.min))
    )
    if end is not None:
        statement = statement.where(MonitorResult.observed_at < end)
    plan = db.execute(
        text(f"EXPLAIN QUERY PLAN {statement.compile(compile_kwargs={'literal_binds': True})}")
    )
    return list(plan)


def compute_monitor_stats(
    db: Session,
    *,
    monitor_id: int,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, float | int]:
    results = fetch_monitor_results(db, monitor_id=monitor_id, start=start, end=end)
    if not results:
        return {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "uptime_percentage": 0.0,
            "avg_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
        }

    success_count = sum(1 for item in results if item.success)
    total_count = len(results)
    aggregated = build_latency_summary([{"latency_ms": float(item.latency_ms)} for item in results])
    return {
        "total_checks": total_count,
        "successful_checks": success_count,
        "failed_checks": total_count - success_count,
        "uptime_percentage": round((success_count / total_count) * 100, 2),
        "avg_latency_ms": float(aggregated["avg_latency_ms"]),
        "p50_latency_ms": float(aggregated["p50_latency_ms"]),
        "p95_latency_ms": float(aggregated["p95_latency_ms"]),
        "p99_latency_ms": float(aggregated["p99_latency_ms"]),
    }


def compute_rollups(
    db: Session,
    *,
    monitor_id: int,
    bucket: str = "hour",
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict[str, float | int | str]]:
    results = fetch_monitor_results(db, monitor_id=monitor_id, start=start, end=end)
    buckets: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "latency_total": 0.0,
        }
    )

    for result in results:
        bucket_key = partition_bucket_for(result.observed_at, bucket=bucket)
        bucket_data = buckets[bucket_key]
        bucket_data["total_checks"] = int(bucket_data["total_checks"]) + 1
        if result.success:
            bucket_data["successful_checks"] = int(bucket_data["successful_checks"]) + 1
        else:
            bucket_data["failed_checks"] = int(bucket_data["failed_checks"]) + 1
        bucket_data["latency_total"] = float(bucket_data["latency_total"]) + float(
            result.latency_ms
        )

    rollups: list[dict[str, float | int | str]] = []
    for bucket_key in sorted(buckets):
        bucket_data = buckets[bucket_key]
        total_checks = int(bucket_data["total_checks"])
        successful_checks = int(bucket_data["successful_checks"])
        failed_checks = int(bucket_data["failed_checks"])
        avg_latency_ms = float(bucket_data["latency_total"]) / total_checks if total_checks else 0.0
        rollups.append(
            {
                "bucket": bucket_key,
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "failed_checks": failed_checks,
                "uptime_percentage": round((successful_checks / total_checks) * 100, 2)
                if total_checks
                else 0.0,
                "avg_latency_ms": round(avg_latency_ms, 2),
            }
        )
    return rollups


__all__ = [
    "compute_monitor_stats",
    "compute_rollups",
    "explain_monitor_result_query",
    "fetch_monitor_results",
]
