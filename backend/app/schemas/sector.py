from pydantic import BaseModel, ConfigDict, Field


class SectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    # Obrigatório só quando quem cria é MASTER (mesmo padrão de tasks/employees).
    store_id: int | None = None


class SectorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    active: bool | None = None


class SectorPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    name: str
    active: bool
