from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import COOKIE_NAME, create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthCredentials, AuthResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: AuthCredentials, response: Response, db: Session = Depends(get_db)
) -> dict[str, User]:
    if db.scalar(select(User).where(User.email == payload.email.lower())) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
        )
    user = User(email=payload.email.lower(), hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=3600,
    )
    return {"user": user}


@router.post("/login", response_model=AuthResponse)
def login(
    payload: AuthCredentials, response: Response, db: Session = Depends(get_db)
) -> dict[str, User]:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user.id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=3600,
    )
    return {"user": user}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
