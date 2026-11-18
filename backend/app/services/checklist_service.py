
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.checklist import ChecklistExecution, ChecklistExecutionItem, ChecklistTemplate, ChecklistTemplateItem
from app.models.employee import Employee
from app.models.user import User
from app.services import audit_service


class ChecklistAlreadyInProgressError(Exception):
    """Já existe uma execução IN_PROGRESS para este template/turno/loja hoje."""


class ChecklistNotInProgressError(Exception):
    """A execução não está (mais) IN_PROGRESS."""


class ChecklistIncompleteError(Exception):
    """Existe item obrigatório sem resposta — não dá para concluir ainda."""

    def __init__(self, missing_item_ids: list[int]) -> None:
        self.missing_item_ids = missing_item_ids
        super().__init__(f"Itens obrigatórios sem resposta: {missing_item_ids}")


def _today(today: date | None = None) -> date:
    return today or datetime.now(timezone.utc).date()


def _has_execution_in_progress_today(
    db: Session, *, template_id: int, shift: str, store_id: int, today: date
) -> bool:
    candidates = db.scalars(
        select(ChecklistExecution).where(
            ChecklistExecution.template_id == template_id,
            ChecklistExecution.shift == shift,
            ChecklistExecution.store_id == store_id,
            ChecklistExecution.status == "IN_PROGRESS",
        )
    )
    return any(execution.started_at.date() == today for execution in candidates)


def start_execution(
    db: Session,
    template: ChecklistTemplate,
    *,
    shift: str,
    actor_name: str,
    user_id: int | None = None,
    employee_id: int | None = None,
    today: date | None = None,
) -> ChecklistExecution:
    if (user_id is None) == (employee_id is None):
        raise ValueError("Informe exatamente um ator: user_id OU employee_id.")

    today = _today(today)

    if _has_execution_in_progress_today(
        db, template_id=template.id, shift=shift, store_id=template.store_id, today=today
    ):
        raise ChecklistAlreadyInProgressError()

    execution = ChecklistExecution(
        template_id=template.id,
        store_id=template.store_id,
        shift=shift,
        executed_by_user_id=user_id,
        executed_by_employee_id=employee_id,
    )
    db.add(execution)
    db.flush()  # precisa do execution.id para gravar os itens e o audit log abaixo

    active_items = db.scalars(
        select(ChecklistTemplateItem)
        .where(ChecklistTemplateItem.template_id == template.id, ChecklistTemplateItem.active.is_(True))
        .order_by(ChecklistTemplateItem.order_index)
    )
    for item in active_items:
        db.add(
            ChecklistExecutionItem(
                checklist_execution_id=execution.id,
                template_item_id=item.id,
                store_id=template.store_id,
                item_description_snapshot=item.description,
            )
        )

    audit_service.log(
        db,
        store_id=template.store_id,
        action="START",
        entity_type="CHECKLIST_EXECUTION",
        entity_id=execution.id,
        actor_user_id=user_id,
        actor_employee_id=employee_id,
        actor_name=actor_name,
        after_data={"template_id": template.id, "shift": shift, "status": "IN_PROGRESS"},
    )

    db.commit()
    db.refresh(execution)
    return execution


def complete_execution(db: Session, execution: ChecklistExecution) -> ChecklistExecution:
    if execution.status != "IN_PROGRESS":
        raise ChecklistNotInProgressError()

    items = db.scalars(
        select(ChecklistExecutionItem)
        .join(ChecklistTemplateItem, ChecklistExecutionItem.template_item_id == ChecklistTemplateItem.id)
        .where(ChecklistExecutionItem.checklist_execution_id == execution.id, ChecklistTemplateItem.required.is_(True))
    )
    missing_item_ids = [item.id for item in items if item.response is None]
    if missing_item_ids:
        raise ChecklistIncompleteError(missing_item_ids)

    execution.status = "COMPLETED"
    execution.finished_at = datetime.now(timezone.utc)
    db.add(execution)

    if execution.executed_by_user_id is not None:
        actor_name = db.get(User, execution.executed_by_user_id).name
        actor_kwargs: dict[str, int] = {"actor_user_id": execution.executed_by_user_id}
    else:
        actor_name = db.get(Employee, execution.executed_by_employee_id).name
        actor_kwargs = {"actor_employee_id": execution.executed_by_employee_id}

    audit_service.log(
        db,
        store_id=execution.store_id,
        action="COMPLETE",
        entity_type="CHECKLIST_EXECUTION",
        entity_id=execution.id,
        actor_name=actor_name,
        before_data={"status": "IN_PROGRESS"},
        after_data={"status": "COMPLETED", "finished_at": execution.finished_at.isoformat()},
        **actor_kwargs,
    )

    db.commit()
    db.refresh(execution)
    return execution
