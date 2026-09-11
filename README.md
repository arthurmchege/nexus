# NEXUS

NEXUS is an AI-powered developer operations platform for registering APIs and
continuously monitoring their health, latency, uptime, errors, and incidents.

## Run locally

### Prerequisites

- Docker and Docker Compose
- Git

### Start the stack

```bash
cp .env.example .env
docker compose up --build
```

The services are then available at:

- Frontend: <http://localhost:3001>
- Backend API: <http://localhost:8001>
- API documentation: <http://localhost:8001/docs>
- PostgreSQL: `localhost:5433`
- Redis: `localhost:6380`
- Caddy HTTP proxy: `http://localhost:8080`
- Caddy HTTPS proxy: `https://localhost:8443` (local certificate)

The backend container applies Alembic migrations before starting the API.

For public deployment, configure `NEXUS_DOMAIN`, `CADDY_EMAIL`,
`APP_ENV=production`, and `FRONTEND_ORIGIN=https://NEXUS_DOMAIN` in `.env`.
Point the domain's DNS records at the host and expose ports 80 and 443 so
Caddy can obtain a trusted certificate. See
[`docs/auth-transport-security.md`](docs/auth-transport-security.md).

### Run backend tests

```bash
source .venv/bin/activate
cd backend
pytest
```

## Architecture overview

The monitoring pipeline is organized as:

```text
Scheduler -> Redis queue -> Monitoring workers -> PostgreSQL time-series storage
```

The FastAPI read API queries monitor configuration and persisted monitoring
results. The Next.js dashboard consumes that API to display system summaries,
monitor inventories, history, and aggregate statistics.

## Read API

The current read-focused endpoints are:

- `GET /api/v1/monitors` — paginated monitor inventory
- `GET /api/v1/monitors/{id}` — monitor details
- `GET /api/v1/monitors/{id}/history` — paginated check history
- `GET /api/v1/monitors/{id}/stats` — uptime, latency, counts, and rollups
- `GET /api/v1/monitors/summary` — system-wide monitor summary

The API is currently open and unauthenticated for local development.

Detailed decisions are documented in:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/monitoring/architecture-decisions.md`](docs/monitoring/architecture-decisions.md)
- [`docs/monitoring/read-path-architecture.md`](docs/monitoring/read-path-architecture.md)

## Development notes

- Copy `.env.example` to `.env` for local configuration.
- Do not commit `.env` or other credentials.
- The API currently has no authentication layer; authentication and
  authorization are future work.
