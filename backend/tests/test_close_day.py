
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.task import DAYS_OF_WEEK, TaskExecutionHistory
from app.services.task_assignment_service import close_out_day

PASSWORD = "SenhaForte123!"

_NOW = datetime.now(timezone.utc)
_TODAY = _NOW.date()
_TODAY_WEEKDAY = DAYS_OF_WEEK[_TODAY.weekday()]
_OTHER_WEEKDAY = DAYS_OF_WEEK[(_TODAY.weekday() + 1) % 7]


def test_blocked_assignment_scheduled_today_gets_a_nao_feito_history_row(
    make_store, make_user, make_task, make_task_assignment, make_employee, db_session
):
    store = make_store()
    manager = make_user(email="gestor-close1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Carlos")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Descongelar camarão")
    assignment = make_task_assignment(
        task=task,
        day_of_week=_TODAY_WEEKDAY,
        status="BLOCKED",
        started_at=_NOW - timedelta(hours=2),
        blocked_at=_NOW - timedelta(hours=1),
        block_reason="Faltou camarão no estoque.",
        blocked_by_employee_id=employee.id,
    )

    result = close_out_day(db_session, today=_TODAY)

    assert result == {"closed_blocked": [assignment.id], "skipped_pending": []}

    history = db_session.scalars(
        select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)
    ).one()
    assert history.employee_id == employee.id
    assert history.result == "NAO_FEITO"
    assert history.justification == "Impedimento não resolvido até o fechamento do dia."
    assert history.observation == "Faltou camarão no estoque."
    assert history.worked_duration_seconds == 0


def test_blocked_assignment_with_prior_sessions_computes_real_worked_time(
    make_store,
    make_user,
    make_task,
    make_task_assignment,
    make_employee,
    make_task_execution_session,
    db_session,
):
    store = make_store()
    manager = make_user(email="gestor-close2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Bruna")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    run_started_at = _NOW - timedelta(hours=3)
    assignment = make_task_assignment(
        task=task,
        day_of_week=_TODAY_WEEKDAY,
        status="BLOCKED",
        started_at=run_started_at,
        blocked_at=_NOW - timedelta(hours=1),
        block_reason="Equipamento quebrou.",
        blocked_by_employee_id=employee.id,
    )
    # Sessão fechada ANTES do impedimento: 30min trabalhados de verdade.
    make_task_execution_session(
        assignment=assignment,
        employee_id=employee.id,
        started_at=run_started_at,
        ended_at=run_started_at + timedelta(minutes=30),
    )

    close_out_day(db_session, today=_TODAY)

    history = db_session.scalars(
        select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)
    ).one()
    assert history.employee_id == employee.id
    assert history.worked_duration_seconds == 1800


def test_pending_assignment_scheduled_today_is_only_reported_not_recorded(
    make_store, make_user, make_task, make_task_assignment, db_session
):
    store = make_store()
    manager = make_user(email="gestor-close3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_TODAY_WEEKDAY, status="PENDING")

    result = close_out_day(db_session, today=_TODAY)

    assert result == {"closed_blocked": [], "skipped_pending": [assignment.id]}
    history_count = db_session.scalar(
        select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)
    )
    assert history_count is None


def test_ignores_assignments_scheduled_for_a_different_day_of_week(
    make_store, make_user, make_task, make_task_assignment, make_employee, db_session
):
    store = make_store()
    manager = make_user(email="gestor-close4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    make_task_assignment(
        task=task,
        day_of_week=_OTHER_WEEKDAY,
        status="BLOCKED",
        started_at=_NOW - timedelta(hours=1),
        blocked_at=_NOW,
        block_reason="Não é hoje.",
        blocked_by_employee_id=employee.id,
    )

    result = close_out_day(db_session, today=_TODAY)

    assert result == {"closed_blocked": [], "skipped_pending": []}


def test_ignores_in_progress_and_completed_assignments(
    make_store, make_user, make_task, make_task_assignment, make_employee, db_session
):
    store = make_store()
    manager = make_user(email="gestor-close5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task_in_progress = make_task(store_id=store.id, created_by_user_id=manager.id, title="Em andamento")
    task_completed = make_task(store_id=store.id, created_by_user_id=manager.id, title="Já concluída")
    make_task_assignment(
        task=task_in_progress,
        day_of_week=_TODAY_WEEKDAY,
        status="IN_PROGRESS",
        started_at=_NOW - timedelta(minutes=30),
        started_by_employee_id=employee.id,
    )
    make_task_assignment(
        task=task_completed,
        day_of_week=_TODAY_WEEKDAY,
        status="COMPLETED",
        started_at=_NOW - timedelta(hours=1),
        completed_at=_NOW - timedelta(minutes=30),
        result="FEITO",
    )

    result = close_out_day(db_session, today=_TODAY)

    assert result == {"closed_blocked": [], "skipped_pending": []}


def test_running_twice_the_same_day_does_not_duplicate_the_history_row(
    make_store, make_user, make_task, make_task_assignment, make_employee, db_session
):
    store = make_store()
    manager = make_user(email="gestor-close6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    make_task_assignment(
        task=task,
        day_of_week=_TODAY_WEEKDAY,
        status="BLOCKED",
        started_at=_NOW - timedelta(hours=1),
        blocked_at=_NOW,
        block_reason="Motivo qualquer.",
        blocked_by_employee_id=employee.id,
    )

    first_result = close_out_day(db_session, today=_TODAY)
    second_result = close_out_day(db_session, today=_TODAY)

    assert first_result["closed_blocked"] != []
    assert second_result == {"closed_blocked": [], "skipped_pending": []}

    history_rows = db_session.scalars(
        select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)
    ).all()
    assert len(history_rows) == 1
