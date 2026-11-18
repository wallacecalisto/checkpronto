
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import exists, func, literal, select
from sqlalchemy import insert as sa_insert
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.task import DAYS_OF_WEEK, TaskAssignment, TaskExecutionHistory
from app.models.task_execution_block import TaskExecutionBlock
from app.models.task_execution_session import TaskExecutionSession
from app.services import store_settings_service

_DAY_INDEX = {day: index for index, day in enumerate(DAYS_OF_WEEK)}  # MONDAY=0 ... SUNDAY=6, igual a date.weekday()


class TaskAssignmentNotPendingError(Exception):
    """O agendamento não está (mais) PENDING."""


class TaskAssignmentNotInProgressError(Exception):
    """O agendamento não está IN_PROGRESS."""


class EmployeeNotInSectorError(Exception):
    """O funcionário não pertence ao setor deste agendamento."""


class EmployeeHasActiveTaskError(Exception):
    """O funcionário já tem uma sessão aberta em OUTRA tarefa — só uma por vez."""


class EmployeeAlreadyInTaskError(Exception):
    """O funcionário já tem uma sessão aberta NESTA MESMA tarefa."""


class NoActiveSessionError(Exception):
    """O funcionário não tem uma sessão aberta nesta tarefa pra fechar."""


class TaskAssignmentNotBlockedError(Exception):
    """O agendamento não está BLOCKED."""


class PhotoProofRequiredError(Exception):
    """A tarefa exige foto (`Task.requires_photo_proof`) e nenhuma foi enviada."""


class MaxAssigneesReachedError(Exception):
    """A execução já tem `store_settings.max_assignees_per_task` sessões abertas."""


class EmployeeNotParticipatingError(Exception):
    pass


def current_day_of_week(today: date | None = None) -> str:
    today = today or datetime.now(timezone.utc).date()
    return DAYS_OF_WEEK[today.weekday()]


def _last_occurrence_date(day_of_week: str, today: date) -> date:
    """A data mais recente (<= hoje) que cai nesse dia da semana."""
    target_index = _DAY_INDEX[day_of_week]
    delta = (today.weekday() - target_index) % 7
    return today - timedelta(days=delta)


def apply_weekly_reset(db: Session, assignment: TaskAssignment, today: date | None = None) -> bool:
    if assignment.status == "PENDING":
        return False

    last_activity = assignment.completed_at or assignment.started_at
    if last_activity is None:
        return False

    today = today or datetime.now(timezone.utc).date()
    last_occurrence = _last_occurrence_date(assignment.day_of_week, today)

    if last_activity.date() >= last_occurrence:
        return False

    now = datetime.now(timezone.utc)
    db.execute(
        sa_update(TaskExecutionSession)
        .where(TaskExecutionSession.task_assignment_id == assignment.id)
        .where(TaskExecutionSession.ended_at.is_(None))
        .values(ended_at=now)
    )
    db.execute(
        sa_update(TaskExecutionBlock)
        .where(TaskExecutionBlock.task_assignment_id == assignment.id)
        .where(TaskExecutionBlock.ended_at.is_(None))
        .values(ended_at=now)
    )

    assignment.status = "PENDING"
    assignment.started_at = None
    assignment.completed_at = None
    assignment.started_by_employee_id = None
    assignment.completed_by_employee_id = None
    assignment.started_by_user_id = None
    assignment.completed_by_user_id = None
    assignment.result = None
    assignment.justification = None
    assignment.observation = None
    assignment.photo_url = None
    assignment.blocked_at = None
    assignment.block_reason = None
    assignment.blocked_by_employee_id = None
    db.add(assignment)
    db.flush()
    return True


def apply_weekly_reset_bulk(db: Session, assignments: list[TaskAssignment], today: date | None = None) -> None:
    resets = [apply_weekly_reset(db, assignment, today=today) for assignment in assignments]
    if any(resets):
        db.commit()


_CLOSEOUT_JUSTIFICATION = "Impedimento não resolvido até o fechamento do dia."


def close_out_day(db: Session, *, today: date | None = None) -> dict[str, list[int]]:
    resolved_today = today or datetime.now(timezone.utc).date()
    today_weekday = DAYS_OF_WEEK[resolved_today.weekday()]
    day_start = datetime.combine(resolved_today, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(resolved_today, time.max, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    stuck_assignments = list(
        db.scalars(
            select(TaskAssignment)
            .where(TaskAssignment.day_of_week == today_weekday)
            .where(TaskAssignment.status.in_(("PENDING", "BLOCKED")))
        )
    )

    closed_blocked: list[int] = []
    skipped_pending: list[int] = []

    for assignment in stuck_assignments:
        if assignment.status == "PENDING":
            skipped_pending.append(assignment.id)
            continue

        already_closed = db.scalar(
            select(TaskExecutionHistory.id)
            .where(TaskExecutionHistory.task_id == assignment.task_id)
            .where(TaskExecutionHistory.store_id == assignment.store_id)
            .where(TaskExecutionHistory.completed_at.between(day_start, day_end))
            .where(TaskExecutionHistory.justification == _CLOSEOUT_JUSTIFICATION)
            .limit(1)
        )
        if already_closed is not None:
            continue

        run_started_at = assignment.started_at
        group_id = uuid.uuid4()
        sessions = list(
            db.scalars(
                select(TaskExecutionSession)
                .where(TaskExecutionSession.task_assignment_id == assignment.id)
                .where(TaskExecutionSession.started_at >= run_started_at)
            )
        )
        worked_seconds_by_employee: dict[int, int] = defaultdict(int)
        for session in sessions:
            if session.ended_at is None:
                session.ended_at = now
            session.execution_group_id = group_id
            db.add(session)
            worked_seconds_by_employee[session.employee_id] += int(
                (session.ended_at - session.started_at).total_seconds()
            )

        db.execute(
            sa_update(TaskExecutionBlock)
            .where(TaskExecutionBlock.task_assignment_id == assignment.id)
            .where(TaskExecutionBlock.started_at >= run_started_at)
            .values(execution_group_id=group_id)
        )

        if not worked_seconds_by_employee:
            worked_seconds_by_employee[assignment.blocked_by_employee_id] = 0

        for participant_employee_id, worked_seconds in worked_seconds_by_employee.items():
            db.add(
                TaskExecutionHistory(
                    store_id=assignment.store_id,
                    task_id=assignment.task_id,
                    task_title=assignment.task.title,
                    employee_id=participant_employee_id,
                    started_at=run_started_at,
                    completed_at=now,
                    result="NAO_FEITO",
                    estimated_duration_minutes=assignment.task.estimated_duration_minutes,
                    justification=_CLOSEOUT_JUSTIFICATION,
                    observation=assignment.block_reason,
                    worked_duration_seconds=worked_seconds,
                    execution_group_id=group_id,
                )
            )
        closed_blocked.append(assignment.id)

    db.commit()
    return {"closed_blocked": closed_blocked, "skipped_pending": skipped_pending}


def _has_open_session_anywhere(employee_id: int):
    return exists().where(TaskExecutionSession.employee_id == employee_id).where(TaskExecutionSession.ended_at.is_(None))


def start_assignment(db: Session, assignment: TaskAssignment, *, employee: Employee) -> TaskAssignment:
    if employee.sector_id != assignment.sector_id:
        raise EmployeeNotInSectorError()

    now = datetime.now(timezone.utc)
    query = (
        sa_update(TaskAssignment)
        .where(TaskAssignment.id == assignment.id, TaskAssignment.status == "PENDING")
        .where(~_has_open_session_anywhere(employee.id))
    )
    result = db.execute(query.values(status="IN_PROGRESS", started_at=now, started_by_employee_id=employee.id))

    if result.rowcount == 0:
        db.refresh(assignment)
        if assignment.status != "PENDING":
            raise TaskAssignmentNotPendingError()
        raise EmployeeHasActiveTaskError()

    db.add(
        TaskExecutionSession(
            task_assignment_id=assignment.id, employee_id=employee.id, store_id=assignment.store_id, started_at=now
        )
    )
    db.refresh(assignment)
    return assignment


def join_assignment(db: Session, assignment: TaskAssignment, *, employee: Employee) -> TaskAssignment:
    if assignment.status != "IN_PROGRESS":
        raise TaskAssignmentNotInProgressError()
    if employee.sector_id != assignment.sector_id:
        raise EmployeeNotInSectorError()

    now = datetime.now(timezone.utc)
    max_assignees = store_settings_service.get_effective_settings(db, assignment.store_id).max_assignees_per_task
    open_here_count = (
        select(func.count()).select_from(TaskExecutionSession).where(
            TaskExecutionSession.task_assignment_id == assignment.id, TaskExecutionSession.ended_at.is_(None)
        )
    )

    select_stmt = select(
        literal(assignment.id), literal(employee.id), literal(assignment.store_id), literal(now)
    ).where(~_has_open_session_anywhere(employee.id))
    if max_assignees is not None and max_assignees > 0:
        select_stmt = select_stmt.where(open_here_count.scalar_subquery() < max_assignees)

    stmt = (
        sa_insert(TaskExecutionSession)
        .from_select(["task_assignment_id", "employee_id", "store_id", "started_at"], select_stmt)
        .returning(TaskExecutionSession.id)
    )
    inserted_id = db.execute(stmt).scalar()

    if inserted_id is None:
        open_here = db.scalar(
            select(TaskExecutionSession.id)
            .where(
                TaskExecutionSession.task_assignment_id == assignment.id,
                TaskExecutionSession.employee_id == employee.id,
                TaskExecutionSession.ended_at.is_(None),
            )
            .limit(1)
        )
        if open_here is not None:
            raise EmployeeAlreadyInTaskError()
        if max_assignees is not None and max_assignees > 0 and db.scalar(open_here_count) >= max_assignees:
            raise MaxAssigneesReachedError()
        raise EmployeeHasActiveTaskError()

    db.refresh(assignment)
    return assignment


def leave_assignment(
    db: Session, assignment: TaskAssignment, *, employee_id: int, leave_reason: str | None = None
) -> TaskAssignment:
    now = datetime.now(timezone.utc)
    result = db.execute(
        sa_update(TaskExecutionSession)
        .where(
            TaskExecutionSession.task_assignment_id == assignment.id,
            TaskExecutionSession.employee_id == employee_id,
            TaskExecutionSession.ended_at.is_(None),
        )
        .values(ended_at=now, leave_reason=leave_reason)
    )
    if result.rowcount == 0:
        raise NoActiveSessionError()

    db.refresh(assignment)
    return assignment


def complete_assignment(
    db: Session,
    assignment: TaskAssignment,
    *,
    result: str,
    employee: Employee,
    justification: str | None = None,
    observation: str | None = None,
    photo_url: str | None = None,
    extra_photo_urls: list[str] | None = None,
) -> TaskAssignment:
    if employee.sector_id != assignment.sector_id:
        raise EmployeeNotInSectorError()

    has_active_session = (
        db.scalar(
            select(TaskExecutionSession.id)
            .where(
                TaskExecutionSession.task_assignment_id == assignment.id,
                TaskExecutionSession.employee_id == employee.id,
                TaskExecutionSession.ended_at.is_(None),
            )
            .limit(1)
        )
        is not None
    )
    if not has_active_session:
        raise EmployeeNotParticipatingError()

    if result == "FEITO" and assignment.task.requires_photo_proof and photo_url is None:
        raise PhotoProofRequiredError()

    now = datetime.now(timezone.utc)
    run_started_at = assignment.started_at
    resolved_extra_photo_urls = extra_photo_urls or []

    update_result = db.execute(
        sa_update(TaskAssignment)
        .where(TaskAssignment.id == assignment.id, TaskAssignment.status == "IN_PROGRESS")
        .values(
            status="COMPLETED",
            completed_at=now,
            result=result,
            justification=justification,
            observation=observation,
            photo_url=photo_url,
            extra_photo_urls=resolved_extra_photo_urls,
            completed_by_employee_id=employee.id,
        )
    )
    if update_result.rowcount == 0:
        raise TaskAssignmentNotInProgressError()

    db.refresh(assignment)

    group_id = uuid.uuid4()

    sessions = list(
        db.scalars(
            select(TaskExecutionSession)
            .where(TaskExecutionSession.task_assignment_id == assignment.id)
            .where(TaskExecutionSession.started_at >= run_started_at)
        )
    )
    worked_seconds_by_employee: dict[int, int] = defaultdict(int)
    for session in sessions:
        if session.ended_at is None:
            session.ended_at = now
        session.execution_group_id = group_id
        db.add(session)
        worked_seconds_by_employee[session.employee_id] += int((session.ended_at - session.started_at).total_seconds())

    db.execute(
        sa_update(TaskExecutionBlock)
        .where(TaskExecutionBlock.task_assignment_id == assignment.id)
        .where(TaskExecutionBlock.started_at >= run_started_at)
        .values(execution_group_id=group_id)
    )

    if not worked_seconds_by_employee:
        worked_seconds_by_employee[employee.id] = int((now - run_started_at).total_seconds())

    for participant_employee_id, worked_seconds in worked_seconds_by_employee.items():
        db.add(
            TaskExecutionHistory(
                store_id=assignment.store_id,
                task_id=assignment.task_id,
                task_title=assignment.task.title,
                employee_id=participant_employee_id,
                started_at=run_started_at,
                completed_at=now,
                result=result,
                estimated_duration_minutes=assignment.task.estimated_duration_minutes,
                justification=justification,
                observation=observation,
                photo_url=photo_url,
                extra_photo_urls=resolved_extra_photo_urls,
                worked_duration_seconds=worked_seconds,
                execution_group_id=group_id,
            )
        )

    return assignment


def block_assignment(db: Session, assignment: TaskAssignment, *, employee: Employee, reason: str) -> TaskAssignment:
    if employee.sector_id != assignment.sector_id:
        raise EmployeeNotInSectorError()

    now = datetime.now(timezone.utc)
    run_started_at = assignment.started_at

    update_result = db.execute(
        sa_update(TaskAssignment)
        .where(TaskAssignment.id == assignment.id, TaskAssignment.status == "IN_PROGRESS")
        .values(status="BLOCKED", blocked_at=now, block_reason=reason, blocked_by_employee_id=employee.id)
    )
    if update_result.rowcount == 0:
        raise TaskAssignmentNotInProgressError()

    db.execute(
        sa_update(TaskExecutionSession)
        .where(TaskExecutionSession.task_assignment_id == assignment.id)
        .where(TaskExecutionSession.started_at >= run_started_at)
        .where(TaskExecutionSession.ended_at.is_(None))
        .values(ended_at=now)
    )

    db.add(
        TaskExecutionBlock(
            task_assignment_id=assignment.id,
            store_id=assignment.store_id,
            blocked_by_employee_id=employee.id,
            reason=reason,
            started_at=now,
        )
    )

    db.refresh(assignment)
    return assignment


def resume_assignment(db: Session, assignment: TaskAssignment, *, employee: Employee) -> TaskAssignment:
    if employee.sector_id != assignment.sector_id:
        raise EmployeeNotInSectorError()

    now = datetime.now(timezone.utc)
    query = (
        sa_update(TaskAssignment)
        .where(TaskAssignment.id == assignment.id, TaskAssignment.status == "BLOCKED")
        .where(~_has_open_session_anywhere(employee.id))
    )
    result = db.execute(
        query.values(status="IN_PROGRESS", blocked_at=None, block_reason=None, blocked_by_employee_id=None)
    )

    if result.rowcount == 0:
        db.refresh(assignment)
        if assignment.status != "BLOCKED":
            raise TaskAssignmentNotBlockedError()
        raise EmployeeHasActiveTaskError()

    db.execute(
        sa_update(TaskExecutionBlock)
        .where(TaskExecutionBlock.task_assignment_id == assignment.id)
        .where(TaskExecutionBlock.ended_at.is_(None))
        .values(ended_at=now)
    )

    db.add(
        TaskExecutionSession(
            task_assignment_id=assignment.id, employee_id=employee.id, store_id=assignment.store_id, started_at=now
        )
    )
    db.refresh(assignment)
    return assignment
