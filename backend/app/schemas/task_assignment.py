from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DayOfWeek = Literal["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
TaskAssignmentStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED"]
TaskResult = Literal["FEITO", "NAO_FEITO"]

_PIN_PATTERN = r"^\d{4}$"


class TaskAssignmentCreate(BaseModel):
    task_id: int
    day_of_week: DayOfWeek
    sector_id: int
    shift: str = Field(min_length=1, max_length=50)


class TaskAssignmentUpdate(BaseModel):

    day_of_week: DayOfWeek | None = None
    sector_id: int | None = None
    # Omitido = não altera (mesmo padrão de `day_of_week`/`sector_id` acima).
    shift: str | None = Field(default=None, min_length=1, max_length=50)


class TaskAssignmentParticipant(BaseModel):

    employee_id: int
    employee_name: str
    started_at: datetime


class TaskAssignmentPublic(BaseModel):
    id: int
    task_id: int
    store_id: int
    day_of_week: str
    # Denormalizados do catálogo (Task) só na resposta, pra tela não precisar
    # de uma segunda chamada — nunca gravados de novo no banco a partir daqui.
    task_title: str
    task_description: str | None
    # SLA da tarefa — usado para colorir o cronômetro ao vivo
    # quando o tempo corrido ultrapassa isso.
    estimated_duration_minutes: int | None
    requires_photo_proof: bool
    shift: str

    sector_id: int
    sector_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    started_by_employee_id: int | None
    completed_by_employee_id: int | None
    started_by_user_id: int | None
    completed_by_user_id: int | None
    result: str | None
    justification: str | None
    observation: str | None
    photo_url: str | None
    extra_photo_urls: list[str]
    elapsed_seconds: int | None
    active_participants: list[TaskAssignmentParticipant]
    blocked_at: datetime | None
    block_reason: str | None
    blocked_by_employee_id: int | None
    latest_execution_history_id: int | None


class TaskAssignmentActionRequest(BaseModel):

    employee_id: int | None = None
    pin: str | None = Field(default=None, pattern=_PIN_PATTERN)


class TaskAssignmentLeaveRequest(TaskAssignmentActionRequest):

    leave_reason: str | None = Field(default=None, max_length=500)


class TaskAssignmentBlockRequest(TaskAssignmentActionRequest):

    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _validate_reason(self) -> "TaskAssignmentBlockRequest":
        if not self.reason.strip():
            raise ValueError("O motivo do impedimento é obrigatório.")
        return self


class TaskAssignmentCompleteRequest(BaseModel):
    employee_id: int | None = None
    pin: str | None = Field(default=None, pattern=_PIN_PATTERN)

    result: TaskResult
    justification: str | None = Field(default=None, max_length=1000)
    observation: str | None = Field(default=None, max_length=1000)
    photo_url: str | None = Field(default=None, max_length=500)
    extra_photo_urls: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_justification(self) -> "TaskAssignmentCompleteRequest":
        if self.result == "NAO_FEITO" and not (self.justification and self.justification.strip()):
            raise ValueError("Justificativa é obrigatória quando o resultado é NAO_FEITO.")
        return self


class TaskAssignmentPhotoUploadResponse(BaseModel):

    photo_url: str
