from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role_title: str | None = Field(default=None, max_length=80)
    store_id: int | None = None
    sector_id: int


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role_title: str | None = Field(default=None, max_length=80)
    sector_id: int | None = None
    active: bool | None = None


class EmployeePublic(BaseModel):
    id: int
    store_id: int
    sector_id: int
    name: str
    role_title: str | None
    active: bool
    has_pin: bool
