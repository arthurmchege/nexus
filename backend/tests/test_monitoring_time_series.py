from __future__ import annotations

from datetime import datetime

from app.services.time_series import build_latency_summary, partition_bucket_for


def test_partition_bucket_generation() -> None:
    bucket = partition_bucket_for(datetime(2026, 9, 15, 12, 30, 0))
    assert bucket == "2026-09"


def test_latency_summary_computes_aggregates() -> None:
    summary = build_latency_summary([
        {"latency_ms": 120},
        {"latency_ms": 200},
        {"latency_ms": 400},
        {"latency_ms": 1000},
    ])

    assert summary["count"] == 4
    assert summary["avg_latency_ms"] == 430.0
    assert summary["p95_latency_ms"] == 1000.0
