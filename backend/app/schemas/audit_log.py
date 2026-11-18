from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogPublic(BaseModel):
    id: int
    store_id: int | None
    store_name: str | None
    actor_type: str
    actor_user_id: int | None
    actor_employee_id: int | None
    actor_name: str
    action: str
    entity_type: str
    entity_id: int
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    created_at: datetime
