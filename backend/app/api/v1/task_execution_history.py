from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import StoreScope, get_current_store_scope, require_roles
from app.db.session import get_db
from app.models.employee import Employee
from app.models.task import Task, TaskExecutionHistory
from app.models.task_execution_block import TaskExecutionBlock
from app.models.task_execution_session import TaskExecutionSession
from app.models.user import User
from app.schemas.task_execution_history import (
    TaskExecutionTimeline,
    TaskTimelineBlockEntry,
    TaskTimelineParticipant,
    TaskTimelineSessionEntry,
)

router = APIRouter(prefix="/task-execution-history", tags=["task-execution-history"])

_MANAGE_ROLES = ("MASTER", "GESTOR", "LIDER")
_HISTORY_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada.")


@router.get("/{history_id}/timeline", response_model=TaskExecutionTimeline)
def get_execution_timeline(
    history_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskExecutionTimeline:
    history_row = db.get(TaskExecutionHistory, history_id)
    if history_row is None:
        raise _HISTORY_NOT_FOUND
    scope.require(history_row.store_id)

    group_id = history_row.execution_group_id
    history_rows = list(
        db.scalars(
            select(TaskExecutionHistory)
            .where(TaskExecutionHistory.execution_group_id == group_id)
            .order_by(TaskExecutionHistory.employee_id)
        )
    )
    sessions = list(
        db.scalars(
            select(TaskExecutionSession)
            .where(TaskExecutionSession.execution_group_id == group_id)
            .order_by(TaskExecutionSession.started_at)
        )
    )
    blocks = list(
        db.scalars(
            select(TaskExecutionBlock)
            .where(TaskExecutionBlock.execution_group_id == group_id)
            .order_by(TaskExecutionBlock.started_at)
        )
    )

    task = db.get(Task, history_row.task_id)
    creator = db.get(User, task.created_by_user_id) if task is not None else None

    employee_ids = {row.employee_id for row in history_rows}
    employee_ids |= {session.employee_id for session in sessions}
    employee_ids |= {block.blocked_by_employee_id for block in blocks}
    employees_by_id = (
        {employee.id: employee for employee in db.scalars(select(Employee).where(Employee.id.in_(employee_ids)))}
        if employee_ids
        else {}
    )

    def _employee_name(employee_id: int) -> str:
        employee = employees_by_id.get(employee_id)
        return employee.name if employee is not None else "Funcionário"

    return TaskExecutionTimeline(
        execution_group_id=str(group_id),
        task_id=history_row.task_id,
        task_title=history_row.task_title,
        created_by_user_name=creator.name if creator is not None else "—",
        estimated_duration_minutes=history_row.estimated_duration_minutes,
        started_at=history_row.started_at,
        completed_at=history_row.completed_at,
        total_elapsed_seconds=int((history_row.completed_at - history_row.started_at).total_seconds()),
        result=history_row.result,
        justification=history_row.justification,
        observation=history_row.observation,
        photo_url=history_row.photo_url,
        extra_photo_urls=history_row.extra_photo_urls,
        participants=[
            TaskTimelineParticipant(
                employee_id=row.employee_id,
                employee_name=_employee_name(row.employee_id),
                worked_duration_seconds=row.worked_duration_seconds,
            )
            for row in history_rows
        ],
        sessions=[
            TaskTimelineSessionEntry(
                employee_id=session.employee_id,
                employee_name=_employee_name(session.employee_id),
                started_at=session.started_at,
                ended_at=session.ended_at,
                leave_reason=session.leave_reason,
            )
            for session in sessions
        ],
        blocks=[
            TaskTimelineBlockEntry(
                blocked_by_employee_id=block.blocked_by_employee_id,
                blocked_by_employee_name=_employee_name(block.blocked_by_employee_id),
                reason=block.reason,
                started_at=block.started_at,
                ended_at=block.ended_at,
            )
            for block in blocks
        ],
    )
