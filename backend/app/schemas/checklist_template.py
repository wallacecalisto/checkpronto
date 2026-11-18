from datetime import datetime

from pydantic import BaseModel, Field


class ChecklistTemplateItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    order_index: int = Field(default=0, ge=0)
    required: bool = True
    requires_photo: bool = False


class ChecklistTemplateItemUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    order_index: int | None = Field(default=None, ge=0)
    required: bool | None = None
    requires_photo: bool | None = None
    active: bool | None = None


class ChecklistTemplateItemPublic(BaseModel):
    id: int
    template_id: int
    description: str
    order_index: int
    required: bool
    requires_photo: bool
    active: bool


class ChecklistTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    # Obrigatório só quando quem cria é MASTER (mesmo padrão de tasks/employees).
    store_id: int | None = None
    target_sector_id: int | None = None
    shift: str = Field(min_length=1, max_length=50)
    items: list[ChecklistTemplateItemCreate] = Field(default_factory=list, min_length=1)


class ChecklistTemplateUpdate(BaseModel):

    name: str | None = Field(default=None, min_length=1, max_length=160)
    active: bool | None = None
    # `exclude_unset=True` no endpoint decide: omitido = sem alteração;
    # `null` explícito = volta a ser um checklist de gestão sem setor.
    target_sector_id: int | None = None
    shift: str | None = Field(default=None, min_length=1, max_length=50)


class ChecklistTemplatePublic(BaseModel):
    id: int
    store_id: int
    name: str
    active: bool
    created_by_user_id: int
    target_sector_id: int | None
    shift: str
    created_at: datetime
    items: list[ChecklistTemplateItemPublic]
