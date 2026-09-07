# Contributing to NEXUS

## Local setup

1. Copy `.env.example` to `.env`.
2. Start PostgreSQL, Redis, the backend, and the frontend with
   `docker compose up --build`.
3. Run backend tests with `cd backend && ../.venv/bin/pytest`.

## Change boundaries

Keep changes focused and preserve the separation between:

- scheduler and database claiming
- Redis queue delivery
- monitoring worker execution
- PostgreSQL result persistence
- FastAPI read and management APIs
- Next.js presentation

Changes that affect monitoring execution should include targeted tests for
failure, retry, and idempotency behavior.

## Pull requests

- Use a conventional commit message such as `feat:`, `fix:`, `docs:`, or
  `chore:`.
- Run the relevant tests and formatting checks before opening a pull request.
- Explain behavioral changes, operational trade-offs, and any follow-up work.
- Never commit `.env` files, credentials, generated build output, or local
  virtual environments.
