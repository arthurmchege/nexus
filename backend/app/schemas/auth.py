from datetime import datetime

from pydantic import BaseModel, Field


class AuthCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserOut
