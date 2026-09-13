# Observability

NEXUS emits one JSON object per log line from the backend and monitoring
worker. Records include an UTC timestamp, level, logger, message, event name,
and safe event-specific identifiers. `LOG_LEVEL` controls verbosity and
defaults to `INFO`; use `DEBUG` locally when diagnosing worker heartbeats.

HTTP requests receive an `X-Request-ID` when one is not supplied and the same
ID is returned in the response and available to request handlers. Passwords,
JWTs, reset tokens, cookies, request bodies, webhook payloads, and full
endpoint URLs are intentionally excluded from structured events.

The public `/api/v1/health/metrics` endpoint reports:

- Redis availability
- monitoring queue depth
- active monitor count
- worker heartbeat freshness
- recent check success rate and sample size

The dashboard Overview page displays these values in the System health panel.
The worker refreshes its Redis heartbeat with a 30-second expiry. A missing
heartbeat means the worker has not reported recently; it does not prove that
all checks are failing.

## Future extension

Production deployments can ship these JSON lines to a centralized log
aggregator and replace the development webhook/mock notification channel with
an external alerting provider. Metrics can later be exported to Prometheus
without changing the dashboard contract.
