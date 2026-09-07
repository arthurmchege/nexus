# NEXUS Architecture

NEXUS is split into independent write-path and read-path concerns so monitoring
work can scale without coupling the dashboard to scheduler execution.

## Monitoring pipeline

1. The scheduler finds due, active monitor endpoints.
2. Database row locking prevents concurrent scheduler instances from claiming
   the same endpoint.
3. Claimed jobs are published to the Redis-backed monitoring queue.
4. Workers execute health checks with bounded retries.
5. Monitoring results are persisted to PostgreSQL time-series storage.
6. FastAPI exposes monitor configuration, history, and aggregate statistics.
7. The Next.js dashboard presents the API data to operators.

## Storage and scaling

PostgreSQL stores monitor configuration and monitoring results. Result storage
is partitioned by observation time and indexed by endpoint and timestamp so
time-bounded history and aggregation queries can prune irrelevant partitions.
Redis provides the transient job queue; durable monitoring history remains in
PostgreSQL.

## Reliability boundaries

Database claiming and Redis enqueueing are separate systems, so they cannot be
made one atomic transaction without an additional coordination mechanism. The
current design advances the monitor schedule in the database transaction before
enqueueing. A process failure between those operations can delay a check until
the next scheduled interval; it does not provide exactly-once delivery.

## Current scope

The current API is intended for local development and portfolio demonstration.
Authentication, authorization, incident workflows, and production deployment
hardening remain future milestones.
