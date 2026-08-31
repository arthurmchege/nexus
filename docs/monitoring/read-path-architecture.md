# Monitoring read-path architecture

## 1. Aggregation strategy

### Query-time aggregation

We compute the expensive, time-windowed metrics on read: uptime percentage, latency percentiles, success/error counts, and rollups over hourly and daily buckets. This keeps the write path simple and avoids maintaining a large, error-prone set of materialized aggregate tables before the system has meaningful load.

Why this choice:
- The data model is already durable in PostgreSQL and the query patterns are read-heavy.
- A large monitoring system will benefit from time-bounded queries rather than precomputing every possible window.
- It keeps the first implementation easy to reason about and tune.

### Precomputed aggregates

We do not precompute a full aggregate table yet. The current design only stores raw result rows and uses a bucket helper to group rows by time window. This is intentionally conservative for the current scale: the system is still in an operational foundation phase and should not add a second source of truth without measured need.

Trade-off:
- Query-time aggregation is more compute-heavy for large time windows.
- It is simpler to keep correct and easier to evolve than a large materialized view with stale data risk.

## 2. Pagination strategy

The API uses offset-based pagination (`skip` and `limit`) for the current milestone. It is simple to implement, easy to test, and consistent with the existing endpoints already in the repo.

Why this choice:
- The repo already exposes paginated monitor and history endpoints in this form.
- It keeps the first pass low-risk and avoids introducing a new cursor contract that would require additional client logic.
- It is adequate for moderate result volumes before read-path optimization becomes necessary.

Trade-offs:
- Offset pagination becomes inefficient at very large page numbers.
- It can skip/duplicate rows under concurrent writes in a highly active dataset.
- Cursor pagination would be better long-term for large histories, but that is not necessary for the initial read exposure milestone.

## 3. Partition-aware query design

The schema stores results in time-partitioned buckets using `partition_bucket` and `observed_at`. The aggregation API filters by `endpoint_id` and a bounded time range before grouping, which preserves the ability to prune partitions and avoids full-table scans across all historical data.

Why this is important:
- The query patterns are dominated by recent time windows, which is the common monitoring use case.
- Restricting on both `endpoint_id` and `observed_at` allows the database to reduce the working set dramatically.

Risk to avoid:
- Querying by `endpoint_id` alone and then doing broad in-memory post-processing defeats partition pruning.
- A wide request covering a multi-year range without filtering by `observed_at` would overwhelm the database.

## 4. Caching strategy

No explicit cache is introduced in this milestone.

Reasoning:
- The API is still read-path exposure, not a high-scale production service.
- The workload is dominated by bounded recent windows, which are manageable in memory and index lookups for a first cut.
- A cache would add stale-data and invalidation complexity before the system demonstrates lower-latency bottlenecks.

Staleness tolerance:
- Current aggregate results are effectively fresh at query time and reflect the latest stored checks.
- This is acceptable until the system adds a measurable read latency problem.

## 5. Query-cost protection and rate limiting

The API currently enforces sane bounds on `limit`, `skip`, and time windows. For example, large requests are rejected or clamped rather than allowing unbounded database work.

This does not yet add full production rate limiting or per-user quotas. That is future work.

The design rule for this milestone is to protect the database against clearly abusive requests while staying explicit that the API is not yet hardened against traffic spikes.

## 6. Authentication and authorization status

This API is currently open and unauthenticated by design in the current repo state. This is explicitly not a production-safe configuration.

Required future work:
- API tokens or OAuth-backed user identity
- Role-based access control for monitor management and read access
- Audit logging for admin operations
- TLS and environment-specific auth enforcement

## Summary

This milestone exposes the data that already exists and keeps the read path intentionally simple and index-aware. The core design is to keep the durable source of truth as raw results, apply bounded time-window queries, and layer aggregation on top when needed. It avoids premature materialization and makes the eventual move to more advanced caching or precomputed rollups easier once metrics show real pressure.
