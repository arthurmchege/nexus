from __future__ import annotations

import json
import threading
import uuid
from collections import deque
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import Any

try:
    import redis
except (
    ImportError
):  # pragma: no cover - dependency is expected in runtime, but tests can run without it.
    redis = None  # type: ignore[assignment]


class RedisUnavailableError(RuntimeError):
    pass


@dataclass(slots=True)
class QueueMetrics:
    queue_depth: int
    jobs_processed: int
    jobs_failed: int
    jobs_retried: int
    processing_duration_ms: float


class MonitoringQueue:
    def __init__(
        self,
        *,
        redis_client: Any | None = None,
        stream_name: str = "nexus:monitoring:jobs",
        max_queue_depth: int = 10000,
    ) -> None:
        self.redis_client = redis_client
        self.stream_name = stream_name
        self.max_queue_depth = max_queue_depth
        self._local_queue: deque[str] = deque()
        self._job_records: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._jobs_processed = 0
        self._jobs_failed = 0
        self._jobs_retried = 0

    def _redis_ready(self) -> bool:
        if self.redis_client is None:
            return False
        try:
            return bool(self.redis_client.ping())
        except Exception:
            return False

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): self._normalize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._normalize_value(item) for item in value]
        return value

    def _serialize(self, payload: dict[str, Any]) -> str:
        payload = dict(payload)
        payload.setdefault("enqueued_at", datetime.utcnow().isoformat())
        payload.setdefault("job_id", str(uuid.uuid4()))
        return json.dumps(self._normalize_value(payload), sort_keys=True)

    def enqueue(self, payload: dict[str, Any] | Any) -> str:
        if is_dataclass(payload):
            job_payload = asdict(payload)
        elif hasattr(payload, "job_id") and getattr(payload, "job_id") is not None:
            job_payload = dict(payload.__dict__)
        elif isinstance(payload, dict):
            job_payload = payload
        else:
            job_payload = dict(payload)

        if not isinstance(job_payload, dict):
            raise TypeError("Queue payload must be a dict-like object.")

        job_payload.setdefault("job_id", str(uuid.uuid4()))
        job_payload.setdefault("enqueued_at", datetime.utcnow().isoformat())
        job_payload.setdefault("attempt_number", 0)
        job_payload.setdefault("status", "queued")

        with self._lock:
            if self._redis_ready():
                try:
                    self.redis_client.lpush(self.stream_name, self._serialize(job_payload))
                    self._job_records[job_payload["job_id"]] = job_payload
                    return job_payload["job_id"]
                except Exception:
                    pass

            if len(self._local_queue) >= self.max_queue_depth:
                raise RedisUnavailableError("Queue depth exceeded configured maximum.")

            self._local_queue.append(self._serialize(job_payload))
            self._job_records[job_payload["job_id"]] = job_payload
            return job_payload["job_id"]

    def dequeue(self) -> dict[str, Any] | None:
        with self._lock:
            if self._redis_ready():
                try:
                    raw = self.redis_client.rpop(self.stream_name)
                    if raw is None:
                        return None
                    job = json.loads(raw)
                    job["status"] = "processing"
                    self._job_records[job["job_id"]] = job
                    return job
                except Exception:
                    pass

            if not self._local_queue:
                return None
            raw = self._local_queue.popleft()
            job = json.loads(raw)
            job["status"] = "processing"
            self._job_records[job["job_id"]] = job
            return job

    def mark_processed(self, job_id: str) -> None:
        with self._lock:
            self._jobs_processed += 1
            job = self._job_records.get(job_id, {})
            job["status"] = "succeeded"
            self._job_records[job_id] = job

    def mark_failed(self, job_id: str, *, error: str | None = None) -> None:
        with self._lock:
            self._jobs_failed += 1
            job = self._job_records.get(job_id, {})
            job["status"] = "failed"
            if error is not None:
                job["error"] = error
            self._job_records[job_id] = job

    def mark_retry(
        self, job_id: str, *, next_attempt: int, retry_at: datetime | None = None
    ) -> None:
        with self._lock:
            self._jobs_retried += 1
            job = self._job_records.get(job_id, {})
            job["status"] = "queued"
            job["attempt_number"] = next_attempt
            job["retry_at"] = (retry_at or datetime.utcnow()).isoformat()
            self._job_records[job_id] = job

    def queue_depth(self) -> int:
        with self._lock:
            if self._redis_ready():
                try:
                    return int(self.redis_client.llen(self.stream_name))
                except Exception:
                    pass
            return len(self._local_queue)

    def metrics(self) -> QueueMetrics:
        with self._lock:
            return QueueMetrics(
                queue_depth=self.queue_depth(),
                jobs_processed=self._jobs_processed,
                jobs_failed=self._jobs_failed,
                jobs_retried=self._jobs_retried,
                processing_duration_ms=0.0,
            )


RedisBackedMonitoringQueue = MonitoringQueue

__all__ = [
    "MonitoringQueue",
    "QueueMetrics",
    "RedisBackedMonitoringQueue",
    "RedisUnavailableError",
]
