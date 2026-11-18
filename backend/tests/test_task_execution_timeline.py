
from datetime import datetime, timezone

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.task import DAYS_OF_WEEK, TaskExecutionHistory
from app.models.task_execution_block import TaskExecutionBlock
from app.models.task_execution_session import TaskExecutionSession

ASSIGNMENTS_URL = "/api/v1/task-assignments"
TIMELINE_URL = "/api/v1/task-execution-history"
PASSWORD = "SenhaForte123!"


def _today_day_of_week() -> str:
    return DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]


def _start_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/start"


def _join_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/join"


def _leave_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/leave"


def _block_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/block"


def _resume_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/resume"


def _complete_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/complete"


def _timeline_url(history_id: int) -> str:
    return f"{TIMELINE_URL}/{history_id}/timeline"


def _setup_two_employee_scenario(make_store, make_user, make_task, make_task_assignment, make_employee):
    store = make_store()
    manager = make_user(email=f"gestor-tl-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee_a = make_employee(store_id=store.id, name="A", pin="1111")
    employee_b = make_employee(store_id=store.id, name="B", pin="2222", sector_id=employee_a.sector_id)
    task = make_task(
        store_id=store.id, created_by_user_id=manager.id, title="Fritar 200 empanados", estimated_duration_minutes=20
    )
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee_a.sector_id)
    make_user(email=f"op-tl-{store.id}@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    return store, manager, employee_a, employee_b, task, assignment, f"op-tl-{store.id}@kijapa.com"


# --- retenção permanente do impedimento ---------------------------------------------


def test_block_creates_a_permanent_record_that_survives_resume(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou camarão."},
        headers=headers,
    )
    client.post(_resume_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    # A tarefa voltou a IN_PROGRESS sem block_reason/blocked_at (estado
    # atual limpo) — mas o REGISTRO do impedimento continua no banco.
    get_response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)
    body = get_response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["block_reason"] is None
    assert body["blocked_at"] is None

    block_row = db_session.scalars(
        select(TaskExecutionBlock).where(TaskExecutionBlock.task_assignment_id == assignment.id)
    ).one()
    assert block_row.reason == "Faltou camarão."
    assert block_row.blocked_by_employee_id == employee_a.id
    assert block_row.ended_at is not None


def test_multiple_block_resume_cycles_each_leave_their_own_record(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    for reason in ("Faltou camarão.", "Fritadeira quebrou."):
        client.post(
            _block_url(assignment.id),
            json={"employee_id": employee_a.id, "pin": "1111", "reason": reason},
            headers=headers,
        )
        client.post(_resume_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    block_rows = list(
        db_session.scalars(select(TaskExecutionBlock).where(TaskExecutionBlock.task_assignment_id == assignment.id))
    )
    assert len(block_rows) == 2
    assert {row.reason for row in block_rows} == {"Faltou camarão.", "Fritadeira quebrou."}
    assert all(row.ended_at is not None for row in block_rows)


# --- execution_group_id agrupa sessões, bloqueios e histórico ------------------------


def test_completing_tags_sessions_and_blocks_with_the_same_execution_group_id(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)
    client.post(
        _leave_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222", "leave_reason": "Fui ajudar o caixa."}, headers=headers
    )
    client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )
    client.post(_resume_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )
    assert complete_response.status_code == status.HTTP_200_OK

    history_rows = list(
        db_session.scalars(select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id))
    )
    group_ids = {row.execution_group_id for row in history_rows}
    assert len(group_ids) == 1  # ambos participantes compartilham o MESMO grupo
    group_id = group_ids.pop()

    sessions = list(
        db_session.scalars(select(TaskExecutionSession).where(TaskExecutionSession.task_assignment_id == assignment.id))
    )
    assert len(sessions) >= 3  # A (start), B (join), A (resume)
    assert all(session.execution_group_id == group_id for session in sessions)

    blocks = list(
        db_session.scalars(select(TaskExecutionBlock).where(TaskExecutionBlock.task_assignment_id == assignment.id))
    )
    assert len(blocks) == 1
    assert blocks[0].execution_group_id == group_id


# --- endpoint de timeline --------------------------------------------------------------


def test_timeline_returns_full_anatomy_of_a_collaborative_execution(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)
    client.post(
        _leave_url(assignment.id),
        json={"employee_id": employee_b.id, "pin": "2222", "leave_reason": "Fui ajudar o caixa."},
        headers=headers,
    )
    client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )
    client.post(_resume_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )

    history_row = db_session.scalars(
        select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id, TaskExecutionHistory.employee_id == employee_a.id)
    ).one()

    gestor_headers = auth_headers(f"gestor-tl-{store.id}@kijapa.com", PASSWORD)
    response = client.get(_timeline_url(history_row.id), headers=gestor_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["task_title"] == "Fritar 200 empanados"
    assert body["created_by_user_name"] == manager.name
    assert body["estimated_duration_minutes"] == 20
    assert body["result"] == "FEITO"
    assert body["total_elapsed_seconds"] >= 0

    participant_ids = {p["employee_id"] for p in body["participants"]}
    assert participant_ids == {employee_a.id, employee_b.id}

    assert len(body["sessions"]) >= 3
    leave_reasons = [s["leave_reason"] for s in body["sessions"] if s["leave_reason"]]
    assert leave_reasons == ["Fui ajudar o caixa."]

    assert len(body["blocks"]) == 1
    assert body["blocks"][0]["reason"] == "Faltou insumo."
    assert body["blocks"][0]["blocked_by_employee_id"] == employee_a.id
    assert body["blocks"][0]["ended_at"] is not None


def test_timeline_works_from_any_participants_history_row(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(_join_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)
    client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )

    history_row_b = db_session.scalars(
        select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id, TaskExecutionHistory.employee_id == employee_b.id)
    ).one()

    gestor_headers = auth_headers(f"gestor-tl-{store.id}@kijapa.com", PASSWORD)
    response = client.get(_timeline_url(history_row_b.id), headers=gestor_headers)

    assert response.status_code == status.HTTP_200_OK
    participant_ids = {p["employee_id"] for p in response.json()["participants"]}
    assert participant_ids == {employee_a.id, employee_b.id}


def test_timeline_for_a_solo_execution_has_no_sessions_or_blocks_listed_but_one_participant(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )

    history_row = db_session.scalars(
        select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)
    ).one()

    gestor_headers = auth_headers(f"gestor-tl-{store.id}@kijapa.com", PASSWORD)
    response = client.get(_timeline_url(history_row.id), headers=gestor_headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body["participants"]) == 1
    assert len(body["sessions"]) == 1
    assert body["blocks"] == []


def test_timeline_for_a_legacy_row_without_execution_group_shows_only_itself(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_employee, make_task_execution_history
):
    store = make_store()
    manager = make_user(email="gestor-tl-legacy@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Legado")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa antiga")
    now = datetime.now(timezone.utc)
    history = make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Tarefa antiga",
        started_at=now,
        completed_at=now,
    )
    headers = auth_headers("gestor-tl-legacy@kijapa.com", PASSWORD)

    response = client.get(_timeline_url(history.id), headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body["participants"]) == 1
    assert body["participants"][0]["employee_id"] == employee.id
    assert body["sessions"] == []
    assert body["blocks"] == []


def test_timeline_returns_404_for_nonexistent_history_id(client: TestClient, make_user, auth_headers, make_store):
    store = make_store()
    make_user(email="gestor-tl-404@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-tl-404@kijapa.com", PASSWORD)

    response = client.get(_timeline_url(999999), headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_timeline_respects_tenant_isolation(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_employee, make_task_execution_history
):
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-tl-b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    employee_b = make_employee(store_id=store_b.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id)
    now = datetime.now(timezone.utc)
    history_b = make_task_execution_history(
        store_id=store_b.id, task_id=task_b.id, employee_id=employee_b.id, started_at=now, completed_at=now
    )
    make_user(email="gestor-tl-a@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers_a = auth_headers("gestor-tl-a@kijapa.com", PASSWORD)

    response = client.get(_timeline_url(history_b.id), headers=headers_a)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- TaskAssignmentPublic.latest_execution_history_id --------------------------------


def test_completed_assignment_exposes_latest_execution_history_id(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)

    pending_response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)
    assert pending_response.json()["latest_execution_history_id"] is None

    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    in_progress_response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)
    assert in_progress_response.json()["latest_execution_history_id"] is None

    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )
    history_id = complete_response.json()["latest_execution_history_id"]
    assert history_id is not None

    gestor_headers = auth_headers(f"gestor-tl-{store.id}@kijapa.com", PASSWORD)
    timeline_response = client.get(_timeline_url(history_id), headers=gestor_headers)
    assert timeline_response.status_code == status.HTTP_200_OK
