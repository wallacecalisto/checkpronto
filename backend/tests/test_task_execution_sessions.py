
from datetime import datetime, timedelta, timezone

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.task import DAYS_OF_WEEK, TaskExecutionHistory
from app.models.task_execution_session import TaskExecutionSession

ASSIGNMENTS_URL = "/api/v1/task-assignments"
PASSWORD = "SenhaForte123!"


def _today_day_of_week() -> str:
    return DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]


def _start_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/start"


def _join_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/join"


def _leave_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/leave"


def _complete_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/complete"


def _setup_two_employee_scenario(make_store, make_user, make_task, make_task_assignment, make_employee):
    store = make_store()
    manager = make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee_a = make_employee(store_id=store.id, name="A", pin="1111")
    employee_b = make_employee(store_id=store.id, name="B", pin="2222", sector_id=employee_a.sector_id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Fritar 200 empanados")
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee_a.sector_id)
    make_user(email=f"op-{store.id}@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    return store, manager, employee_a, employee_b, task, assignment, f"op-{store.id}@kijapa.com"


# --- entrar (join) -----------------------------------------------------------------


def test_employee_joins_in_progress_assignment_of_same_sector(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    participant_ids = {p["employee_id"] for p in body["active_participants"]}
    assert participant_ids == {employee_a.id, employee_b.id}


def test_employee_cannot_join_pending_assignment(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "TASK_NOT_IN_PROGRESS"


def test_employee_from_another_sector_cannot_join(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, make_sector
):
    store, manager, employee_a, _employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    other_sector = make_sector(store_id=store.id, name="Outro Setor")
    outsider = make_employee(store_id=store.id, name="Forasteiro", pin="3333", sector_id=other_sector.id)
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": outsider.id, "pin": "3333"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_IN_SECTOR"


def test_employee_cannot_join_the_same_task_twice(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "EMPLOYEE_ALREADY_IN_TASK"


def test_employee_cannot_join_a_task_they_themselves_started(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "EMPLOYEE_ALREADY_IN_TASK"


def test_employee_with_active_task_on_a_different_assignment_cannot_join(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    other_task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa 2")
    other_assignment = make_task_assignment(
        task=other_task, day_of_week=_today_day_of_week(), sector_id=employee_a.sector_id
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_start_url(other_assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "EMPLOYEE_HAS_ACTIVE_TASK"


def test_max_assignees_per_task_blocks_join_once_the_limit_is_reached(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    manager_headers = auth_headers(manager.email, PASSWORD)
    client.patch(f"/api/v1/stores/{store.id}/settings", json={"max_assignees_per_task": 1}, headers=manager_headers)

    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "MAX_ASSIGNEES_REACHED"


def test_max_assignees_per_task_set_to_one_reproduces_v1_individual_mode(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    manager_headers = auth_headers(manager.email, PASSWORD)
    client.patch(f"/api/v1/stores/{store.id}/settings", json={"max_assignees_per_task": 1}, headers=manager_headers)
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "MAX_ASSIGNEES_REACHED"
    # Ninguém entrou de verdade — a tarefa continua com só o funcionário A.
    detail_response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)
    participant_ids = {p["employee_id"] for p in detail_response.json()["active_participants"]}
    assert participant_ids == {employee_a.id}


def test_max_assignees_per_task_zero_means_unlimited(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    manager_headers = auth_headers(manager.email, PASSWORD)
    client.patch(f"/api/v1/stores/{store.id}/settings", json={"max_assignees_per_task": 0}, headers=manager_headers)
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK


def test_store_without_settings_row_has_no_max_assignees_limit(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK


# --- sair (leave) --------------------------------------------------------------------


def test_employee_leaves_assignment_others_keep_working(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    response = client.post(_leave_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert [p["employee_id"] for p in body["active_participants"]] == [employee_a.id]


def test_leave_reason_is_recorded_on_the_closed_session(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    response = client.post(
        _leave_url(assignment.id),
        json={"employee_id": employee_b.id, "pin": "2222", "leave_reason": "Fui ajudar o caixa."},
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK

    closed_session = db_session.scalars(
        select(TaskExecutionSession).where(
            TaskExecutionSession.task_assignment_id == assignment.id,
            TaskExecutionSession.employee_id == employee_b.id,
        )
    ).one()
    assert closed_session.ended_at is not None
    assert closed_session.leave_reason == "Fui ajudar o caixa."

    # A sessão de quem CONTINUA na tarefa não é afetada.
    still_open_session = db_session.scalars(
        select(TaskExecutionSession).where(
            TaskExecutionSession.task_assignment_id == assignment.id,
            TaskExecutionSession.employee_id == employee_a.id,
        )
    ).one()
    assert still_open_session.ended_at is None
    assert still_open_session.leave_reason is None


def test_leave_reason_is_optional(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    response = client.post(
        _leave_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    closed_session = db_session.scalars(
        select(TaskExecutionSession).where(
            TaskExecutionSession.task_assignment_id == assignment.id,
            TaskExecutionSession.employee_id == employee_b.id,
        )
    ).one()
    assert closed_session.leave_reason is None


def test_leaving_without_an_active_session_fails(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    # employee_b nunca entrou nessa tarefa.
    response = client.post(_leave_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "NO_ACTIVE_SESSION"


def test_leaving_frees_employee_to_start_another_task(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    other_task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa 2")
    other_assignment = make_task_assignment(
        task=other_task, day_of_week=_today_day_of_week(), sector_id=employee_a.sector_id
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    blocked = client.post(
        _start_url(other_assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers
    )
    assert blocked.status_code == status.HTTP_409_CONFLICT

    client.post(_leave_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    retry = client.post(
        _start_url(other_assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers
    )
    assert retry.status_code == status.HTTP_200_OK


def test_employee_who_never_joined_cannot_complete(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    # employee_b nunca entrou nesta tarefa — só pertence ao mesmo setor.
    response = client.post(
        _complete_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222", "result": "FEITO"}, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_PARTICIPATING"


def test_employee_who_left_cannot_complete(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)
    client.post(_leave_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    # employee_a já saiu — não pode mais concluir, mesmo tendo iniciado a tarefa.
    response = client.post(
        _complete_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"}, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_PARTICIPATING"

    # employee_b continua dentro — consegue concluir normalmente.
    ok_response = client.post(
        _complete_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222", "result": "FEITO"}, headers=headers
    )
    assert ok_response.status_code == status.HTTP_200_OK


# --- conclusão colaborativa: uma linha de histórico por participante ----------------


def test_completing_collaborative_task_creates_one_history_row_per_participant(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )

    assert complete_response.status_code == status.HTTP_200_OK
    body = complete_response.json()
    assert body["status"] == "COMPLETED"
    assert body["active_participants"] == []  # ninguém "continua dentro" de uma tarefa concluída

    history_rows = list(
        db_session.scalars(select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id))
    )
    assert len(history_rows) == 2
    employee_ids = {row.employee_id for row in history_rows}
    assert employee_ids == {employee_a.id, employee_b.id}
    for row in history_rows:
        assert row.result == "FEITO"
        assert row.worked_duration_seconds is not None and row.worked_duration_seconds >= 0
        # Tempo de PAREDE (started_at/completed_at) é o mesmo pros dois —
        # é o tempo TRABALHADO (worked_duration_seconds) que pode diferir.
        assert row.started_at == history_rows[0].started_at
        assert row.completed_at == history_rows[0].completed_at


def test_employee_who_left_early_still_gets_a_history_row_for_time_worked(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)
    client.post(_leave_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )
    assert complete_response.status_code == status.HTTP_200_OK

    history_rows = list(
        db_session.scalars(select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id))
    )
    assert {row.employee_id for row in history_rows} == {employee_a.id, employee_b.id}


def test_worked_duration_seconds_matches_exact_sum_of_sessions(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_task,
    make_task_assignment,
    make_employee,
    db_session,
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    now = datetime.now(timezone.utc)
    assignment.started_at = now - timedelta(seconds=700)
    db_session.add(assignment)
    db_session.commit()

    session_a = db_session.scalars(
        select(TaskExecutionSession).where(
            TaskExecutionSession.task_assignment_id == assignment.id,
            TaskExecutionSession.employee_id == employee_a.id,
        )
    ).one()
    session_a.started_at = now - timedelta(seconds=600)
    db_session.add(session_a)
    db_session.commit()

    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)
    session_b = db_session.scalars(
        select(TaskExecutionSession).where(
            TaskExecutionSession.task_assignment_id == assignment.id,
            TaskExecutionSession.employee_id == employee_b.id,
        )
    ).one()
    session_b.started_at = now - timedelta(seconds=200)
    db_session.add(session_b)
    db_session.commit()

    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )
    assert complete_response.status_code == status.HTTP_200_OK

    history_by_employee = {
        row.employee_id: row
        for row in db_session.scalars(select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id))
    }
    # Tolerância pequena (latência real de execução do teste) — os dois
    # `ended_at` são o MESMO `now` gravado por `complete_assignment`.
    assert abs(history_by_employee[employee_a.id].worked_duration_seconds - 600) <= 2
    assert abs(history_by_employee[employee_b.id].worked_duration_seconds - 200) <= 2
