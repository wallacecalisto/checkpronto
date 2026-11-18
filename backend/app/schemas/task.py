from datetime import datetime

from pydantic import BaseModel, Field

# --- Catálogo (Task) -------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    # SLA opcional — sem isso, a tarefa nunca é considerada
    # "com atraso" (ver TaskExecutionHistory).
    estimated_duration_minutes: int | None = Field(default=None, ge=1)
    requires_photo_proof: bool = False
    # Obrigatório só para MASTER (que não pertence a nenhuma loja); ignorado
    # para os demais papéis, que sempre criam na própria loja.
    store_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    estimated_duration_minutes: int | None = Field(default=None, ge=1)
    requires_photo_proof: bool | None = None
    active: bool | None = None


class TaskPublic(BaseModel):
    id: int
    store_id: int
    title: str
    description: str | None
    estimated_duration_minutes: int | None
    requires_photo_proof: bool
    active: bool
    created_by_user_id: int
    created_at: datetime
