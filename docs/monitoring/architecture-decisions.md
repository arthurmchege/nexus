# Monitoring architecture decisions

## 1. Scheduling model

NEXUS schedules checks centrally using the database as the source of truth. Each active monitor has a `next_check_at` timestamp. The scheduler selects a bounded batch where `next_check_at <= now` and updates the chosen rows atomically before handing them to the queue. This avoids one timer or task per monitor and keeps scheduling consistent across multiple app instances.

## 2. Why not one timer per monitor?

A timer-per-monitor model does not scale: each instance would create thousands of asyncio tasks or OS threads, which creates memory and scheduling overhead and makes restart behavior fragile. Centralized scheduling follows a single queueing pattern and makes the system easier to run horizontally.

## 3. How jobs enter the queue

A scheduler claims due monitors in a batch, computes the next run time, and enqueues a Redis job containing the monitor ID, attempt count, schedule time, and idempotency key. The queue acts as the durable handoff layer between scheduling and execution.

## 4. How workers consume jobs

Multiple workers consume from the same Redis queue. They process a job only when it is due and mark the job state as `processing` before execution. This allows horizontal scaling without requiring each worker to coordinate through the same in-process memory.

## 5. Duplicate jobs

Redis delivers jobs at least once, not exactly once. NEXUS therefore uses an idempotency key per monitor/job attempt and deduplicates repeated processing for a schedule window. Re-delivery is tolerated; duplicate execution is prevented through a guard on the result record and job state.

## 6. Worker crashes

When a worker crashes while a job is `processing`, the job is treated as recoverable. The queue keeps the job in a recoverable state until lease expiration or a worker heartbeat indicates it is abandoned. Re-delivery then retry-schedules the job.

## 7. Redis outage behavior

If Redis is unavailable, the scheduler stops enqueueing new work and the worker stops consuming new jobs. The API remains available, but monitoring execution is temporarily paused. This is a safe failure mode because the system does not silently drop work; it degrades gracefully instead of failing a whole request path.

## 8. Retry behavior

Retries are bounded and based on failure classification. Network timeouts, DNS failures, and transient connection errors are retried with exponential backoff. Permanent failures such as invalid URLs or SSRF-blocked addresses are not retried indefinitely.

## 9. Backpressure

The scheduler caps each batch and workers enforce maximum concurrency. The Redis queue is bounded by the scheduler’s batch size and worker capacity. If queue depth grows, the system slows scheduling rather than growing without limit.

## 10. Result persistence

Each job writes a structured result record after the health check completes. Results are stored alongside metadata such as latency, status code, response size, success/failure, and classified error category. PostgreSQL remains the durable source of truth for recent and operational data.

## 11. How the results table scales

The raw result table is not treated as a small app table. For higher scale, the design moves to monthly time-based partitions keyed by `observed_at`, with pruning/retention applied per partition. This retains query locality for recent data while avoiding unbounded table growth.

## 12. Historical retention and aggregation

Raw data is retained for a short period, then aggregated into hourly and daily rollups for uptime, latency percentiles, error rates, and status mix. Aggregated tables are cheaper to query than the raw results table and are the basis for dashboards and alerting.

## 13. PostgreSQL responsibilities

PostgreSQL owns durable monitor metadata, result storage, recent state, scheduler claims, and transactional coordination. It is the operational source of truth and the place for strong consistency.

## 14. Redis responsibilities

Redis owns the ready queue, delayed retries, job lease metadata, and quick coordination signals. It is optimized for low-latency enqueue/dequeue, but it is not the durable system of record.

## 15. Worker responsibilities

Workers own network IO, timeout enforcement, HTTP probing, result serialization, and idempotent result writing. They are stateless and horizontally scalable.

## 16. Current vs. future

This milestone implements the foundation for centralized scheduling, Redis-backed jobs, and time-series-aware result storage. It does not claim infinite scalability or exact-once delivery. The current platform is designed for disciplined, bounded growth rather than magical scale.
