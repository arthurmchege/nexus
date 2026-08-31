from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime


def partition_bucket_for(observed_at: datetime, *, bucket: str = "month") -> str:
    bucket_name = bucket.lower()
    if bucket_name == "hour":
        return observed_at.strftime("%Y-%m-%dT%H:00")
    if bucket_name == "day":
        return observed_at.strftime("%Y-%m-%d")
    return observed_at.strftime("%Y-%m")


def build_latency_summary(results: Iterable[dict[str, object]]) -> dict[str, float | int]:
    values = [float(result.get("latency_ms", 0)) for result in results if isinstance(result, dict)]
    if not values:
        return {"count": 0, "avg_latency_ms": 0.0, "p50_latency_ms": 0.0, "p95_latency_ms": 0.0, "p99_latency_ms": 0.0}

    ordered = sorted(values)
    count = len(ordered)
    avg_latency_ms = sum(ordered) / count
    p50_index = max(0, min(count - 1, int(count * 0.50)))
    p95_index = max(0, min(count - 1, int(count * 0.95)))
    p99_index = max(0, min(count - 1, int(count * 0.99)))
    return {
        "count": count,
        "avg_latency_ms": round(avg_latency_ms, 2),
        "p50_latency_ms": round(ordered[p50_index], 2),
        "p95_latency_ms": round(ordered[p95_index], 2),
        "p99_latency_ms": round(ordered[p99_index], 2),
    }


__all__ = ["build_latency_summary", "partition_bucket_for"]
