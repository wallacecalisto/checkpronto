from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Shift = Literal["MANHA", "TARDE", "NOITE"]
ChecklistItemResponse = Literal["OK", "DIVERGENTE"]
ChecklistValidationResult = Literal["APROVADO", "DIVERGENTE"]

_PIN_PATTERN = r"^\d{4}$"


class ChecklistExecutionCreate(BaseModel):

    template_id: int
    shift: Shift
    employee_id: int | None = None
    pin: str | None = Field(default=None, pattern=_PIN_PATTERN)


class ChecklistValidationRequest(BaseModel):
    result: ChecklistValidationResult
    justification: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _validate_justification(self) -> "ChecklistValidationRequest":
        if self.result == "DIVERGENTE" and not (self.justification and self.justification.strip()):
            raise ValueError("Justificativa é obrigatória quando o resultado é DIVERGENTE.")
        return self


class ChecklistValidationPublic(BaseModel):
    id: int
    checklist_execution_item_id: int
    validated_by_user_id: int
    validated_at: datetime
    result: str
    justification: str | None
    original_response_snapshot: dict


class ChecklistExecutionItemAnswerRequest(BaseModel):
    response: ChecklistItemResponse
    observation: str | None = Field(default=None, max_length=1000)
    photo_url: str | None = None
    extra_photo_urls: list[str] = Field(default_factory=list)


class ChecklistExecutionItemPublic(BaseModel):
    id: int
    checklist_execution_id: int
    template_item_id: int
    item_description_snapshot: str
    response: str | None
    observation: str | None
    photo_url: str | None
    extra_photo_urls: list[str]
    requires_photo: bool
    validation: ChecklistValidationPublic | None


class ChecklistItemPhotoUploadResponse(BaseModel):
    photo_url: str


class ChecklistExecutionPublic(BaseModel):
    id: int
    template_id: int
    template_name: str
    store_id: int
    shift: str
    executed_by_user_id: int | None
    executed_by_employee_id: int | None
    executed_by_name: str
    validated_by_names: list[str]
    started_at: datetime
    finished_at: datetime | None
    status: str
    fully_validated: bool
    items: list[ChecklistExecutionItemPublic]
