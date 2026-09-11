# Password reset

Password reset uses a cryptographically random, single-use token generated
with `secrets.token_urlsafe(32)`. Only its SHA-256 digest is stored in Redis,
with a 15-minute TTL. Redis `GETDEL` makes consumption atomic, preventing a
token from being reused concurrently.

The request endpoint always returns the same success message whether the
email exists. It is protected by the existing Redis limiter: three requests
per email per hour and ten requests per trusted client IP per 15 minutes.
The reset endpoint returns a generic invalid-or-expired error for unknown,
expired, or already-consumed tokens.

Reset links are logged only in development mode. There is no email provider
configured in this project. Production delivery should connect the logged
link extension point to a provider such as Resend, SendGrid, or Amazon SES.

Users have a `password_changed_at` timestamp. New JWTs include `iat`, and the
authentication dependency rejects tokens issued before that timestamp. This
invalidates active sessions after a successful password reset without changing
the existing JWT cookie design.
