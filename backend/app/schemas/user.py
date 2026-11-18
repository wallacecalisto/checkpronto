from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Espelha app.models.user.USER_ROLES (CHECK constraint do banco) — se um papel
# novo for adicionado lá, precisa ser adicionado aqui também.
UserRole = Literal["MASTER", "GESTOR", "LIDER", "OPERACIONAL"]


class UserPublic(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    store_id: int | None
    active: bool
    must_change_password: bool


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    role: UserRole
    store_id: int | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = None
    store_id: int | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=255)
