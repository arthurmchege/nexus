# NEXUS authentication and ownership

NEXUS uses bcrypt password hashes and short-lived, signed JWTs stored in an
`httpOnly` cookie. Bcrypt is intentionally slow and salted, which makes stolen
password hashes substantially harder to crack than fast general-purpose hashes.
JWTs avoid a server-side session lookup on every request while Redis remains
available for queueing; the cookie is not readable by browser JavaScript.

Sessions expire after `JWT_EXPIRE_MINUTES` (60 minutes by default). There is no
refresh token yet: an expired session requires a new login. The cookie is
`SameSite=Lax`, `httpOnly`, and should be marked `secure` when deployed over
HTTPS.

Every monitor and alert route depends on `get_current_user`. Monitor queries
filter by `owner_id`; detail, mutation, history, stats, result ingestion, and
alert queries return 404 for another user's monitor. Incidents and deliveries
derive ownership through their monitor relationship, avoiding duplicated
ownership columns at the cost of a join for alert listing.

The ownership migration creates a configurable admin account using
`ADMIN_EMAIL` and `ADMIN_PASSWORD`, then assigns all pre-authentication
monitors to it. Deployments must replace the development default password
before exposing the service. New monitors are assigned to the authenticated
user.

Login/signup rate limiting, password reset, email verification, and OAuth are
deferred. They are required before treating the public deployment as a
production identity system.
