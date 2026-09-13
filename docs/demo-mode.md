# Public read-only demo mode

NEXUS seeds a dedicated `demo@nexus.local` account through the
`20260913_demo_account` Alembic migration. The account is marked with the
`users.is_demo` flag, which is intentionally a boolean rather than an email
convention so it can later evolve into a role or permission model.

The migration creates four owned monitors with representative up, down, and
degraded states, recent check history, one open incident, one resolved
incident, and delivered alert records. It is applied automatically with the
normal migration command. To restore the dataset, downgrade to
`20260912_password_reset` and upgrade to head; this is not required during
normal operation because demo sessions cannot mutate the data.

`POST /api/v1/auth/demo-login` issues the same secure, HTTP-only session cookie
as ordinary login without exposing credentials. The endpoint only authenticates
the seeded demo user. Read endpoints remain available, while every monitor
mutation (create, update, activate, deactivate, delete, and result submission)
depends on `require_writable_user` and returns HTTP 403 with
`Demo accounts are read-only.` for demo sessions. The frontend hides mutation
controls as a usability improvement, but the API dependency is the security
boundary.

No periodic reset job is needed: read-only enforcement prevents vandalism and
keeps the seeded dataset stable. A reset remains available through the
migration downgrade/upgrade procedure if the seed is intentionally changed.
