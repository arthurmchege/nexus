# Alerting architecture

## State evaluation

Each monitor has a persisted health state and counters for consecutive
failures and successes. The default policy moves a monitor from `UP` to
`DEGRADED` after one failed check, then to `DOWN` after two consecutive
failures. Two consecutive successes recover either state to `UP`. A single
failed check is therefore visible without opening an incident. The thresholds
are stored per monitor so a noisy or latency-sensitive endpoint can be
configured independently.

## Incidents and deliveries

An incident is the durable health episode for one monitor. It has an open or
resolved status, timestamps, and the transition reason. A unique partial
database index allows at most one open incident per monitor.

An alert delivery is a separate record for one incident event and channel. Its
deduplication key is `(incident, event, channel)`, preventing repeated
evaluation or request retries from sending the same notification twice.

## Notification channels

The channel interface is asynchronous and receives a structured event. The
initial real channel is an HTTP webhook using a bounded timeout. A mock channel
is included for deterministic tests and local development. Webhook delivery is
at-least-once: failed sends are retried up to three attempts with exponential
backoff, after which the delivery is marked failed and logged. There is no
claim of exactly-once external delivery because the remote endpoint may accept
a request and fail before the client receives its response.

## Flapping and concurrency

Consecutive thresholds suppress isolated blips. While an incident is open,
additional failures do not create another incident or delivery. Recovery
requires the success threshold, so boundary flapping does not repeatedly open
and resolve an incident. State evaluation locks the monitor row in a database
transaction; the unique open-incident constraint is the final race safeguard.

## Scope and trade-offs

The first implementation evaluates state synchronously with result persistence
to keep the transition durable and observable. A later scale milestone can
move dispatch to an outbox/worker without changing the incident contract. The
current API is open and unauthenticated, consistent with the rest of the local
development stack.
