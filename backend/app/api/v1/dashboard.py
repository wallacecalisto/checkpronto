
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import StoreScope, get_current_store_scope, require_roles
from app.db.session import get_db
from app.models.checklist import ChecklistExecution, ChecklistExecutionItem, ChecklistValidation
from app.models.employee import Employee
from app.models.task import DAYS_OF_WEEK, Task, TaskAssignment, TaskExecutionHistory
from app.models.user import User
from app.schemas.dashboard import (
    ActivityFeedEntry,
    DashboardSummary,
    EmployeeProfile,
    EmployeeProfileTaskEntry,
    EmployeeRankingEntry,
    ExceptionEntry,
    RecentChecklistEntry,
    WeeklyTrendPoint,
)
from app.services import task_assignment_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_MANAGE_ROLES = ("MASTER", "GESTOR", "LIDER")
_EMPLOYEE_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado.")


def _resolve_period_dates(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    resolved_end = end_date or today
    resolved_start = start_date or (resolved_end - timedelta(days=6))
    return resolved_start, resolved_end


def _resolve_period(start_date: date | None, end_date: date | None) -> tuple[datetime, datetime]:
    resolved_start, resolved_end = _resolve_period_dates(start_date, end_date)
    return (
        datetime.combine(resolved_start, time.min, tzinfo=timezone.utc),
        datetime.combine(resolved_end, time.max, tzinfo=timezone.utc),
    )


def _days_of_week_in_range(start_date: date, end_date: date) -> set[str]:
    if (end_date - start_date).days >= 6:
        return set(DAYS_OF_WEEK)
    days: set[str] = set()
    current = start_date
    while current <= end_date:
        days.add(DAYS_OF_WEEK[current.weekday()])
        current += timedelta(days=1)
    return days


def _resolve_store_id(current_user: User, store_id: int | None) -> int | None:
    if current_user.role == "MASTER":
        return store_id
    return current_user.store_id


def _is_on_time(row: TaskExecutionHistory) -> bool | None:
    if row.result != "FEITO" or row.estimated_duration_minutes is None:
        return None
    duration_minutes = row.worked_duration_seconds / 60
    return duration_minutes <= row.estimated_duration_minutes


def _completed_only(rows: list[TaskExecutionHistory]) -> list[TaskExecutionHistory]:
    return [row for row in rows if row.result == "FEITO"]


def _sla_breakdown(rows: list[TaskExecutionHistory]) -> tuple[int, int, float | None]:
    sla_rows = [row for row in _completed_only(rows) if row.estimated_duration_minutes is not None]
    if not sla_rows:
        return 0, 0, None
    on_time_count = sum(1 for row in sla_rows if _is_on_time(row))
    late_count = len(sla_rows) - on_time_count
    return on_time_count, late_count, on_time_count / len(sla_rows) * 100


def _avg_execution_seconds(rows: list[TaskExecutionHistory]) -> float | None:
    completed_rows = _completed_only(rows)
    if not completed_rows:
        return None
    durations = [row.worked_duration_seconds for row in completed_rows]
    return sum(durations) / len(durations)


def _history_in_period(db: Session, *, store_id: int | None, start: datetime, end: datetime) -> list[TaskExecutionHistory]:
    query = select(TaskExecutionHistory).where(TaskExecutionHistory.completed_at.between(start, end))
    if store_id is not None:
        query = query.where(TaskExecutionHistory.store_id == store_id)
    return list(db.scalars(query))


# --- /summary (pending = agora, via task_assignments; completed = período, via history) ----


def _pending_tasks_now(db: Session, *, store_id: int | None, allowed_days: set[str]) -> int:
    query = select(TaskAssignment).join(Task, TaskAssignment.task_id == Task.id).where(Task.active.is_(True))
    if store_id is not None:
        query = query.where(TaskAssignment.store_id == store_id)
    assignments = list(db.scalars(query))
    task_assignment_service.apply_weekly_reset_bulk(db, assignments)
    return sum(
        1
        for assignment in assignments
        if assignment.status in ("PENDING", "IN_PROGRESS", "BLOCKED") and assignment.day_of_week in allowed_days
    )


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> DashboardSummary:
    resolved_start_date, resolved_end_date = _resolve_period_dates(start_date, end_date)
    start, end = _resolve_period(start_date, end_date)
    scoped_store_id = _resolve_store_id(current_user, store_id)

    allowed_days = _days_of_week_in_range(resolved_start_date, resolved_end_date)
    pending_tasks = _pending_tasks_now(db, store_id=scoped_store_id, allowed_days=allowed_days)
    completed_tasks = len(_completed_only(_history_in_period(db, store_id=scoped_store_id, start=start, end=end)))
    total_tasks = pending_tasks + completed_tasks
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks else 0.0

    divergent_query = select(ChecklistValidation).where(
        ChecklistValidation.result == "DIVERGENTE",
        ChecklistValidation.validated_at.between(start, end),
    )
    if scoped_store_id is not None:
        divergent_query = divergent_query.where(ChecklistValidation.store_id == scoped_store_id)
    checklist_divergent_count = len(list(db.scalars(divergent_query)))

    return DashboardSummary(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        completion_rate=completion_rate,
        checklist_divergent_count=checklist_divergent_count,
    )


# --- /ranking e /weekly-trend (exclusivamente task_execution_history) -------------


@router.get("/ranking", response_model=list[EmployeeRankingEntry])
def get_ranking(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    sector_id: int | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> list[EmployeeRankingEntry]:
    start, end = _resolve_period(start_date, end_date)
    scoped_store_id = _resolve_store_id(current_user, store_id)

    history = _completed_only(_history_in_period(db, store_id=scoped_store_id, start=start, end=end))

    by_employee: dict[int, list[TaskExecutionHistory]] = defaultdict(list)
    for row in history:
        by_employee[row.employee_id].append(row)

    entries: list[EmployeeRankingEntry] = []
    for employee_id, rows in by_employee.items():
        employee = db.get(Employee, employee_id)
        if employee is None:
            continue
        if sector_id is not None and employee.sector_id != sector_id:
            continue

        on_time_count, late_count, on_time_rate = _sla_breakdown(rows)
        entries.append(
            EmployeeRankingEntry(
                employee_id=employee.id,
                employee_name=employee.name,
                completed_count=len(rows),
                avg_execution_seconds=_avg_execution_seconds(rows),
                on_time_count=on_time_count,
                late_count=late_count,
                on_time_rate=on_time_rate,
            )
        )

    entries.sort(key=lambda entry: entry.avg_execution_seconds if entry.avg_execution_seconds is not None else float("inf"))
    return entries[:limit]


@router.get("/weekly-trend", response_model=list[WeeklyTrendPoint])
def get_weekly_trend(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> list[WeeklyTrendPoint]:
    start, end = _resolve_period(start_date, end_date)
    scoped_store_id = _resolve_store_id(current_user, store_id)

    # NAO_FEITO fora da contagem/tempo médio — ver _completed_only.
    history = _completed_only(_history_in_period(db, store_id=scoped_store_id, start=start, end=end))

    by_day: dict[str, list[TaskExecutionHistory]] = defaultdict(list)
    for row in history:
        # .weekday(): 0=segunda..6=domingo, mesma ordem de DAYS_OF_WEEK — igual
        # ao mesmo cálculo já usado em task_assignment_service.current_day_of_week.
        by_day[DAYS_OF_WEEK[row.completed_at.weekday()]].append(row)

    points = []
    for day in DAYS_OF_WEEK:
        rows = by_day.get(day, [])
        points.append(
            WeeklyTrendPoint(day_of_week=day, completed_count=len(rows), avg_execution_seconds=_avg_execution_seconds(rows))
        )
    return points


# --- /employees/{id}/profile ("Raio-X Individual") --------------------------------


@router.get("/employees/{employee_id}/profile", response_model=EmployeeProfile)
def get_employee_profile(
    employee_id: int,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> EmployeeProfile:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise _EMPLOYEE_NOT_FOUND
    scope.require(employee.store_id)

    start, end = _resolve_period(start_date, end_date)
    rows = list(
        db.scalars(
            select(TaskExecutionHistory)
            .where(TaskExecutionHistory.employee_id == employee_id)
            .where(TaskExecutionHistory.completed_at.between(start, end))
            .order_by(TaskExecutionHistory.completed_at.desc())
        )
    )

    on_time_count, late_count, on_time_rate = _sla_breakdown(rows)
    tasks = [
        EmployeeProfileTaskEntry(
            id=row.id,
            task_title=row.task_title,
            started_at=row.started_at,
            completed_at=row.completed_at,
            result=row.result,
            estimated_duration_minutes=row.estimated_duration_minutes,
            duration_seconds=row.worked_duration_seconds,
            on_time=_is_on_time(row),
            justification=row.justification,
            observation=row.observation,
            photo_url=row.photo_url,
        )
        for row in rows
    ]

    return EmployeeProfile(
        employee_id=employee.id,
        employee_name=employee.name,
        completed_count=len(_completed_only(rows)),
        avg_execution_seconds=_avg_execution_seconds(rows),
        on_time_count=on_time_count,
        late_count=late_count,
        on_time_rate=on_time_rate,
        tasks=tasks,
    )


# --- /activity-feed (sempre "hoje", nunca o período filtrado) ---------------------


@router.get("/activity-feed", response_model=list[ActivityFeedEntry])
def get_activity_feed(
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    limit: int = Query(default=20, ge=1, le=100),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> list[ActivityFeedEntry]:
    scoped_store_id = _resolve_store_id(current_user, store_id)
    if start_date is None and end_date is None:
        today = datetime.now(timezone.utc).date()
        start = datetime.combine(today, time.min, tzinfo=timezone.utc)
        end = datetime.combine(today, time.max, tzinfo=timezone.utc)
    else:
        start, end = _resolve_period(start_date, end_date)

    entries: list[ActivityFeedEntry] = []

    history_query = select(TaskExecutionHistory).where(TaskExecutionHistory.completed_at.between(start, end))
    if scoped_store_id is not None:
        history_query = history_query.where(TaskExecutionHistory.store_id == scoped_store_id)
    for row in db.scalars(history_query):
        employee = db.get(Employee, row.employee_id)
        actor_name = employee.name if employee is not None else "Funcionário"
        entries.append(
            ActivityFeedEntry(
                id=f"task:{row.id}",
                actor_name=actor_name,
                description=f'concluiu "{row.task_title}"',
                occurred_at=row.completed_at,
            )
        )

    validation_query = select(ChecklistValidation).where(ChecklistValidation.validated_at.between(start, end))
    if scoped_store_id is not None:
        validation_query = validation_query.where(ChecklistValidation.store_id == scoped_store_id)
    for row in db.scalars(validation_query):
        validator = db.get(User, row.validated_by_user_id)
        actor_name = validator.name if validator is not None else "Usuário"
        entries.append(
            ActivityFeedEntry(
                id=f"validation:{row.id}",
                actor_name=actor_name,
                description="validou um item de checklist",
                occurred_at=row.validated_at,
            )
        )

    entries.sort(key=lambda entry: entry.occurred_at, reverse=True)
    return entries[:limit]


# --- /exceptions ---------------------------------


@router.get("/exceptions", response_model=list[ExceptionEntry])
def get_exceptions(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> list[ExceptionEntry]:
    start, end = _resolve_period(start_date, end_date)
    scoped_store_id = _resolve_store_id(current_user, store_id)

    entries: list[ExceptionEntry] = []

    task_query = (
        select(TaskExecutionHistory)
        .where(TaskExecutionHistory.completed_at.between(start, end))
        .where(
            or_(
                TaskExecutionHistory.result == "NAO_FEITO",
                TaskExecutionHistory.observation.is_not(None),
            )
        )
    )
    if scoped_store_id is not None:
        task_query = task_query.where(TaskExecutionHistory.store_id == scoped_store_id)

    employees_by_id = {employee.id: employee for employee in db.query(Employee).all()}
    for row in db.scalars(task_query):
        entries.append(
            ExceptionEntry(
                id=f"task:{row.id}",
                type="TAREFA",
                title=row.task_title,
                user_name=employees_by_id[row.employee_id].name
                if row.employee_id in employees_by_id
                else "Funcionário",
                date=row.completed_at,
                reason=row.justification or row.observation,
            )
        )

    validation_query = select(ChecklistValidation).where(
        ChecklistValidation.result == "DIVERGENTE",
        ChecklistValidation.validated_at.between(start, end),
    )
    if scoped_store_id is not None:
        validation_query = validation_query.where(ChecklistValidation.store_id == scoped_store_id)

    for row in db.scalars(validation_query):
        execution_item = db.get(ChecklistExecutionItem, row.checklist_execution_item_id)
        execution = db.get(ChecklistExecution, execution_item.checklist_execution_id) if execution_item else None
        executor = db.get(User, execution.executed_by_user_id) if execution is not None else None
        entries.append(
            ExceptionEntry(
                id=f"checklist:{row.id}",
                type="CHECKLIST",
                title=execution_item.item_description_snapshot if execution_item is not None else "Item de checklist",
                user_name=executor.name if executor is not None else "Usuário",
                date=row.validated_at,
                reason=row.justification,
            )
        )

    blocked_query = (
        select(TaskAssignment)
        .join(Task, TaskAssignment.task_id == Task.id)
        .where(TaskAssignment.status == "BLOCKED")
        .where(TaskAssignment.blocked_at.between(start, end))
        .where(Task.active.is_(True))
    )
    if scoped_store_id is not None:
        blocked_query = blocked_query.where(TaskAssignment.store_id == scoped_store_id)

    for row in db.scalars(blocked_query):
        reporter_id = row.blocked_by_employee_id
        entries.append(
            ExceptionEntry(
                id=f"impedimento:{row.id}",
                type="IMPEDIMENTO",
                title=row.task.title,
                user_name=employees_by_id[reporter_id].name if reporter_id in employees_by_id else "Funcionário",
                date=row.blocked_at,
                reason=row.block_reason,
            )
        )

    entries.sort(key=lambda entry: entry.date, reverse=True)
    return entries[:limit]


# --- /recent-checklists -------------------------------------------------


@router.get("/recent-checklists", response_model=list[RecentChecklistEntry])
def get_recent_checklists(
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    limit: int = Query(default=5, ge=1, le=200),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> list[RecentChecklistEntry]:
    scoped_store_id = _resolve_store_id(current_user, store_id)

    query = select(ChecklistExecution).order_by(ChecklistExecution.started_at.desc())
    if scoped_store_id is not None:
        query = query.where(ChecklistExecution.store_id == scoped_store_id)
    if start_date is not None or end_date is not None:
        start, end = _resolve_period(start_date, end_date)
        query = query.where(ChecklistExecution.started_at.between(start, end))

    executions = list(db.scalars(query.limit(limit)))
    entries: list[RecentChecklistEntry] = []
    for execution in executions:
        items = execution.items
        executor = db.get(User, execution.executed_by_user_id)
        validator_ids = {item.validation.validated_by_user_id for item in items if item.validation is not None}
        validators = [db.get(User, user_id) for user_id in validator_ids]
        fully_validated = all(item.validation is not None for item in items if item.response is not None)
        entries.append(
            RecentChecklistEntry(
                id=execution.id,
                template_name=execution.template.name,
                shift=execution.shift,
                status=execution.status,
                fully_validated=fully_validated,
                executed_by_name=executor.name if executor is not None else "Usuário",
                validated_by_names=sorted(validator.name for validator in validators if validator is not None),
                started_at=execution.started_at,
                finished_at=execution.finished_at,
            )
        )
    return entries
