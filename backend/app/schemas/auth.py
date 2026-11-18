from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserPublic

__all__ = ["ChangePasswordRequest", "LoginRequest", "TokenResponse", "UserPublic"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ChangePasswordRequest(BaseModel):

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=255)
