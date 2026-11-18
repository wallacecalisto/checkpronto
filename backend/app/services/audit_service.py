
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log(
    db: Session,
    *,
    store_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int,
    actor_name: str,
    actor_user_id: int | None = None,
    actor_employee_id: int | None = None,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
) -> AuditLog:
    if (actor_user_id is None) == (actor_employee_id is None):
        raise ValueError("Informe exatamente um ator: actor_user_id OU actor_employee_id.")

    entry = AuditLog(
        store_id=store_id,
        actor_type="USER" if actor_user_id is not None else "EMPLOYEE",
        actor_user_id=actor_user_id,
        actor_employee_id=actor_employee_id,
        actor_name=actor_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before_data,
        after_data=after_data,
    )
    db.add(entry)
    return entry


def action_for_update(updates: dict[str, Any]) -> str:
    if set(updates.keys()) == {"active"}:
        return "ACTIVATE" if updates["active"] else "DEACTIVATE"
    return "UPDATE"
