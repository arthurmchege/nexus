# Authentication rate limiting

Login and signup are protected by Redis-backed fixed-window counters. Keys
include both the normalized email and client IP, so rotating one identity
does not bypass all protection while a shared network is not blocked by one
user's failed attempts.

## Limits

- Login: 5 attempts per email per 15 minutes and 20 attempts per IP per hour.
- Signup: 3 attempts per email per hour and 10 attempts per IP per 15 minutes.

The limits are intentionally separate because password guessing and account
creation abuse have different patterns. A successful login clears the
current email counter. Exceeding a limit returns `429 Too Many Requests` with
`Retry-After`, which is exposed through CORS so the browser can show the
remaining wait time.

The implementation uses fixed windows rather than a sliding window to keep
the Redis operation atomic and inexpensive across multiple backend instances.
The boundary can permit a short burst across adjacent windows; this is an
acceptable trade-off for the initial deployment.

If Redis is unavailable, authentication fails closed with `503` rather than
allowing unbounded password guessing or signup abuse. Operators should
monitor Redis availability because this intentionally makes Redis part of the
authentication request path.
