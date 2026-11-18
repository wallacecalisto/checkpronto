
from datetime import datetime, timedelta, timezone

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.task import DAYS_OF_WEEK, TaskAssignment, TaskExecutionHistory
from app.models.task_execution_block import TaskExecutionBlock
from app.models.task_execution_session import TaskExecutionSession

ASSIGNMENTS_URL = "/api/v1/task-assignments"
DASHBOARD_URL = "/api/v1/dashboard"
PASSWORD = "SenhaForte123!"


def _today_day_of_week() -> str:
    return DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]


def _start_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/start"


def _block_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/block"


def _resume_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/resume"


def _complete_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/complete"


def _setup_two_employee_scenario(make_store, make_user, make_task, make_task_assignment, make_employee):
    store = make_store()
    manager = make_user(email=f"gestor-blk-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee_a = make_employee(store_id=store.id, name="A", pin="1111")
    employee_b = make_employee(store_id=store.id, name="B", pin="2222", sector_id=employee_a.sector_id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Descongelar camarão")
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee_a.sector_id)
    make_user(email=f"op-blk-{store.id}@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    return store, manager, employee_a, employee_b, task, assignment, f"op-blk-{store.id}@kijapa.com"


# --- reportar impedimento (block) ---------------------------------------------------


def test_reporting_impediment_without_reason_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(
        _block_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_reporting_impediment_with_blank_reason_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "   "},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_reporting_impediment_on_a_pending_task_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)

    response = client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "TASK_NOT_IN_PROGRESS"


def test_employee_from_another_sector_cannot_report_impediment(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, make_sector
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    other_sector = make_sector(store_id=store.id, name="Outro Setor")
    outsider = make_employee(store_id=store.id, name="Forasteiro", pin="3333", sector_id=other_sector.id)
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    response = client.post(
        _block_url(assignment.id),
        json={"employee_id": outsider.id, "pin": "3333", "reason": "Faltou insumo."},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_IN_SECTOR"


def test_reporting_impediment_closes_all_active_sessions_and_freezes_the_clock(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(
        f"{ASSIGNMENTS_URL}/{assignment.id}/join", json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers
    )

    response = client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou camarão no estoque."},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert body["block_reason"] == "Faltou camarão no estoque."
    assert body["blocked_at"] is not None
    assert body["blocked_by_employee_id"] == employee_a.id
    assert body["active_participants"] == []

    open_sessions = list(
        db_session.scalars(
            select(TaskExecutionSession)
            .where(TaskExecutionSession.task_assignment_id == assignment.id)
            .where(TaskExecutionSession.ended_at.is_(None))
        )
    )
    assert open_sessions == []

    # Ambos podem começar OUTRA tarefa agora — a trava de tarefa simultânea
    # não os prende mais, porque as sessões foram fechadas.
    other_task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa 2")
    other_assignment = make_task_assignment(
        task=other_task, day_of_week=_today_day_of_week(), sector_id=employee_a.sector_id
    )
    retry = client.post(
        _start_url(other_assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers
    )
    assert retry.status_code == status.HTTP_200_OK


def test_elapsed_seconds_freezes_at_blocked_at(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    block_response = client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )
    frozen_elapsed = block_response.json()["elapsed_seconds"]
    assert frozen_elapsed is not None

    # Uma segunda leitura, um pouco depois, tem que mostrar o MESMO valor —
    # não o relógio continuando a correr.
    get_response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)
    assert get_response.json()["elapsed_seconds"] == frozen_elapsed


def test_resuming_does_not_count_the_blocked_period_towards_elapsed_seconds(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    now = datetime.now(timezone.utc)
    assignment_row = db_session.get(TaskAssignment, assignment.id)
    assignment_row.started_at = now - timedelta(seconds=300)
    db_session.add(assignment_row)
    db_session.commit()

    block_response = client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )
    assert block_response.status_code == status.HTTP_200_OK

    block_row = db_session.scalars(
        select(TaskExecutionBlock).where(TaskExecutionBlock.task_assignment_id == assignment.id)
    ).one()
    block_row.started_at = now - timedelta(seconds=250)
    block_row.ended_at = now - timedelta(seconds=50)
    db_session.add(block_row)
    db_session.commit()

    resume_response = client.post(
        _resume_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers
    )
    assert resume_response.status_code == status.HTTP_200_OK

    get_response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)
    elapsed = get_response.json()["elapsed_seconds"]
    # Sem descontar o impedimento (200s), o cronômetro mostraria ~300s
    # (started_at até agora). Descontando, fica em torno de 100s.
    assert 90 <= elapsed <= 115


# --- retomar (resume) ----------------------------------------------------------------


def test_resuming_a_non_blocked_task_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)

    response = client.post(
        _resume_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "TASK_NOT_BLOCKED"


def test_employee_from_another_sector_cannot_resume(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, make_sector
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    other_sector = make_sector(store_id=store.id, name="Outro Setor")
    outsider = make_employee(store_id=store.id, name="Forasteiro", pin="3333", sector_id=other_sector.id)
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )

    response = client.post(
        _resume_url(assignment.id), json={"employee_id": outsider.id, "pin": "3333"}, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_IN_SECTOR"


def test_employee_with_active_task_elsewhere_cannot_resume(
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
    client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )
    client.post(_start_url(other_assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    response = client.post(
        _resume_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "EMPLOYEE_HAS_ACTIVE_TASK"


def test_resuming_reopens_a_session_and_clears_block_fields(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )

    response = client.post(
        _resume_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["blocked_at"] is None
    assert body["block_reason"] is None
    assert body["blocked_by_employee_id"] is None
    assert [p["employee_id"] for p in body["active_participants"]] == [employee_b.id]


# --- fluxo completo: iniciar -> bloquear -> retomar -> concluir --------------------


def test_full_flow_start_block_resume_complete_excludes_blocked_time_from_worked_seconds(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)

    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    # Empurra a sessão de employee_a 100s pro passado, pra ter um tempo
    # trabalhado PRÉ-bloqueio determinístico.
    now = datetime.now(timezone.utc)
    pre_block_session = db_session.scalars(
        select(TaskExecutionSession).where(
            TaskExecutionSession.task_assignment_id == assignment.id, TaskExecutionSession.employee_id == employee_a.id
        )
    ).one()
    pre_block_session.started_at = now - timedelta(seconds=100)
    db_session.add(pre_block_session)
    assignment_row = db_session.get(TaskAssignment, assignment.id)
    assignment_row.started_at = now - timedelta(seconds=100)
    db_session.add(assignment_row)
    db_session.commit()

    block_response = client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )
    assert block_response.status_code == status.HTTP_200_OK

    resume_response = client.post(
        _resume_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers
    )
    assert resume_response.status_code == status.HTTP_200_OK
    assert resume_response.json()["status"] == "IN_PROGRESS"

    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "result": "FEITO"},
        headers=headers,
    )
    assert complete_response.status_code == status.HTTP_200_OK

    history = db_session.scalars(
        select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)
    ).one()
    assert 100 <= history.worked_duration_seconds <= 105


def test_stale_blocked_assignment_resets_to_pending(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    stale = datetime.now(timezone.utc) - timedelta(days=8)
    blocked_assignment = make_task_assignment(
        task=task,
        day_of_week=_today_day_of_week(),
        sector_id=employee_a.sector_id,
        status="BLOCKED",
        started_at=stale - timedelta(minutes=5),
        blocked_at=stale,
        block_reason="Impedimento da semana passada.",
        blocked_by_employee_id=employee_a.id,
    )

    response = client.get(f"{ASSIGNMENTS_URL}/{blocked_assignment.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["blocked_at"] is None
    assert body["block_reason"] is None


# --- alerta ao gestor (dashboard) ----------------------------------------------------


def test_blocked_task_appears_in_dashboard_exceptions_as_impedimento(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou camarão no estoque."},
        headers=headers,
    )

    gestor_headers = auth_headers(f"gestor-blk-{store.id}@kijapa.com", PASSWORD)
    response = client.get(f"{DASHBOARD_URL}/exceptions", headers=gestor_headers)

    assert response.status_code == status.HTTP_200_OK
    entries = response.json()
    impedimentos = [entry for entry in entries if entry["type"] == "IMPEDIMENTO"]
    assert len(impedimentos) == 1
    assert impedimentos[0]["title"] == "Descongelar camarão"
    assert impedimentos[0]["reason"] == "Faltou camarão no estoque."
    assert impedimentos[0]["user_name"] == "A"


def test_blocked_task_still_counts_as_pending_in_summary(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
):
    store, manager, employee_a, employee_b, task, assignment, op_email = _setup_two_employee_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    client.post(
        _block_url(assignment.id),
        json={"employee_id": employee_a.id, "pin": "1111", "reason": "Faltou insumo."},
        headers=headers,
    )

    gestor_headers = auth_headers(f"gestor-blk-{store.id}@kijapa.com", PASSWORD)
    response = client.get(f"{DASHBOARD_URL}/summary", headers=gestor_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["pending_tasks"] == 1
