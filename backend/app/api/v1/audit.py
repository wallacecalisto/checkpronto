from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogPublic

router = APIRouter(prefix="/audit", tags=["audit"])


def _to_public(entry: AuditLog) -> AuditLogPublic:
    return AuditLogPublic(
        id=entry.id,
        store_id=entry.store_id,
        store_name=entry.store.name if entry.store else None,
        actor_type=entry.actor_type,
        actor_user_id=entry.actor_user_id,
        actor_employee_id=entry.actor_employee_id,
        actor_name=entry.actor_name,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        before_data=entry.before_data,
        after_data=entry.after_data,
        created_at=entry.created_at,
    )


@router.get("", response_model=list[AuditLogPublic])
def list_audit_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    actor_user_id: int | None = Query(default=None),
    actor_employee_id: int | None = Query(default=None),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    date_from: date | None = Query(default=None, description="Filtra created_at >= este dia (UTC), inclusive."),
    date_to: date | None = Query(default=None, description="Filtra created_at <= este dia (UTC), inclusive."),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER", "GESTOR")),
) -> list[AuditLogPublic]:
    query = select(AuditLog)

    if current_user.role == "MASTER":
        if store_id is not None:
            query = query.where(AuditLog.store_id == store_id)
    else:
        query = query.where(AuditLog.store_id == current_user.store_id)

    if action is not None:
        query = query.where(AuditLog.action == action)
    if entity_type is not None:
        query = query.where(AuditLog.entity_type == entity_type)
    if actor_user_id is not None:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
    if actor_employee_id is not None:
        query = query.where(AuditLog.actor_employee_id == actor_employee_id)
    # "Dia" aqui é o dia em UTC — mesma simplificação já usada no filtro de
    # data de GET /checklists.
    if date_from is not None:
        query = query.where(AuditLog.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to is not None:
        query = query.where(AuditLog.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))

    entries = db.scalars(query.order_by(AuditLog.created_at.desc())).all()
    return [_to_public(entry) for entry in entries]
