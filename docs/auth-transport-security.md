# Authentication transport security

NEXUS uses a signed JWT in the `nexus_session` HTTP-only cookie. The JWT
claims, bcrypt password hashing, and ownership checks are unchanged by this
configuration.

## Cookie policy

The cookie is issued with:

- `HttpOnly`: always enabled, preventing JavaScript access.
- `SameSite=Lax`: appropriate for a same-site dashboard while still allowing
  normal top-level navigation; NEXUS is not an embedded cross-site widget.
- No `Domain`: the browser scopes the cookie to the host that issued it.
- `Secure`: enabled when `APP_ENV=production`, disabled for local HTTP
  development and tests.

Set `APP_ENV=production` only when the application is reached through HTTPS.
Local Compose development keeps `APP_ENV=development` and uses the direct
ports `http://localhost:3001` and `http://localhost:8001`.

## TLS termination

Caddy is included in Compose as the production-facing reverse proxy. It
routes `/api/*` to FastAPI and all other paths to Next.js. For deployment:

1. Point DNS `A`/`AAAA` records for `NEXUS_DOMAIN` at the host.
2. Set `NEXUS_DOMAIN` in `.env`.
3. Set `APP_ENV=production` and `FRONTEND_ORIGIN=https://yourdomain.com`.
4. Expose ports 80 and 443.
5. Start with `docker compose up --build -d`.

Caddy obtains and renews a public certificate automatically once DNS and
network reachability are correct. The default `localhost` configuration is
for local proxy smoke tests only and is not public TLS.

## CORS

FastAPI allows credentials only from the single `FRONTEND_ORIGIN` value. It
is `http://localhost:3001` in development and must be set to the exact HTTPS
deployment origin in production; it is never configured as `*`.
