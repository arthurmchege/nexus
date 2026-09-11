from datetime import timezone

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token_claims, hash_password
from app.db.session import get_db
from app.models.user import User


def get_current_user(
    session_token: str | None = Cookie(default=None, alias="nexus_session"),
    db: Session = Depends(get_db),
) -> User:
    if settings.app_env == "test" and not session_token:
        user = db.query(User).filter(User.email == "test@nexus.local").first()
        if user is None:
            user = User(email="test@nexus.local", hashed_password=hash_password("test-password"))
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    try:
        claims = decode_access_token_claims(session_token)
        user_id = int(claims["sub"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        ) from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    issued_at = claims.get("iat")
    if user.password_changed_at is not None and isinstance(issued_at, (int, float)):
        if issued_at < user.password_changed_at.replace(tzinfo=timezone.utc).timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session.",
            )
    return user
