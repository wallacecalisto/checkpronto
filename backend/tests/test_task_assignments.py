
from datetime import datetime, timedelta, timezone

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.task import DAYS_OF_WEEK, TaskExecutionHistory

ASSIGNMENTS_URL = "/api/v1/task-assignments"
PASSWORD = "SenhaForte123!"


def _today_day_of_week() -> str:
    return DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]


def _start_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/start"


def _complete_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/complete"


# --- criação --------------------------------------------------------------------


def test_gestor_creates_assignment(client: TestClient, make_user, auth_headers, make_store, make_task, make_sector):
    store = make_store()
    manager = make_user(email="gestor-ta1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Fazer 150 filadélfias")
    sector = make_sector(store_id=store.id, name="Cozinha Quente")
    headers = auth_headers("gestor-ta1@kijapa.com", PASSWORD)

    response = client.post(
        ASSIGNMENTS_URL,
        json={"task_id": task.id, "day_of_week": "MONDAY", "sector_id": sector.id, "shift": "Manhã"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["task_title"] == "Fazer 150 filadélfias"
    assert body["day_of_week"] == "MONDAY"
    assert body["sector_id"] == sector.id
    assert body["sector_name"] == "Cozinha Quente"
    assert body["status"] == "PENDING"
    assert body["estimated_duration_minutes"] is None
    assert body["active_participants"] == []
    assert body["shift"] == "Manhã"


def test_assignment_denormalizes_task_estimated_duration_minutes(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_sector
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ta1b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id, estimated_duration_minutes=15)
    sector = make_sector(store_id=store.id)
    headers = auth_headers("gestor-ta1b@kijapa.com", PASSWORD)

    response = client.post(
        ASSIGNMENTS_URL,
        json={"task_id": task.id, "day_of_week": "MONDAY", "sector_id": sector.id, "shift": "Geral"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["estimated_duration_minutes"] == 15


def test_operacional_cannot_create_assignment(client: TestClient, make_user, auth_headers, make_store, make_task):
    store = make_store()
    manager = make_user(email="gestor-ta3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    make_user(email="op-ta-create@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-create@kijapa.com", PASSWORD)

    response = client.post(ASSIGNMENTS_URL, json={"task_id": task.id, "day_of_week": "MONDAY"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_operational_assignment_requires_sector_id(
    client: TestClient, make_user, auth_headers, make_store, make_task
):
    store = make_store()
    manager = make_user(email="gestor-ta1b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-ta1b@kijapa.com", PASSWORD)

    response = client.post(ASSIGNMENTS_URL, json={"task_id": task.id, "day_of_week": "MONDAY"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = response.json()
    assert any("sector_id" in str(error.get("loc")) for error in body["errors"])


def test_cannot_create_assignment_with_sector_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_sector
):
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_a = make_user(email="gestor-a-ta-sec@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    task_a = make_task(store_id=store_a.id, created_by_user_id=manager_a.id)
    sector_b = make_sector(store_id=store_b.id)
    headers = auth_headers("gestor-a-ta-sec@kijapa.com", PASSWORD)

    response = client.post(
        ASSIGNMENTS_URL,
        json={"task_id": task_a.id, "day_of_week": "MONDAY", "sector_id": sector_b.id, "shift": "Geral"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_cannot_create_assignment_for_task_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_task
):
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-b-ta@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id)
    make_user(email="gestor-a-ta@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-a-ta@kijapa.com", PASSWORD)

    response = client.post(
        ASSIGNMENTS_URL,
        json={"task_id": task_b.id, "day_of_week": "MONDAY", "sector_id": 1, "shift": "Geral"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- listagem / filtro por dia da semana -------------------------------------------


def test_filter_assignments_by_day_of_week(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    make_task_assignment(task=task, day_of_week="MONDAY")
    make_task_assignment(task=task, day_of_week="TUESDAY")
    headers = auth_headers("gestor-ta4@kijapa.com", PASSWORD)

    response = client.get(f"{ASSIGNMENTS_URL}?day_of_week=MONDAY", headers=headers)

    assignments = response.json()
    assert len(assignments) == 1
    assert assignments[0]["day_of_week"] == "MONDAY"


def test_assignments_of_deleted_task_disappear_from_listing(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta20@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    active_task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Continua ativa")
    deleted_task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Vai ser excluída", active=False)
    make_task_assignment(task=active_task, day_of_week="MONDAY")
    make_task_assignment(task=deleted_task, day_of_week="TUESDAY")
    headers = auth_headers("gestor-ta20@kijapa.com", PASSWORD)

    response = client.get(ASSIGNMENTS_URL, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    titles = {assignment["task_title"] for assignment in response.json()}
    assert titles == {"Continua ativa"}


def test_gestor_cannot_view_assignment_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-b-ta2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id)
    assignment_b = make_task_assignment(task=task_b, day_of_week="MONDAY")
    make_user(email="gestor-a-ta2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-a-ta2@kijapa.com", PASSWORD)

    response = client.get(f"{ASSIGNMENTS_URL}/{assignment_b.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- edição / exclusão -------------------------------------------------------------


def test_gestor_edits_assignment_day_and_sector(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_sector
):
    store = make_store()
    manager = make_user(email="gestor-ta7@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week="MONDAY")
    sector = make_sector(store_id=store.id, name="Sushi")
    headers = auth_headers("gestor-ta7@kijapa.com", PASSWORD)

    response = client.patch(
        f"{ASSIGNMENTS_URL}/{assignment.id}",
        json={"day_of_week": "FRIDAY", "sector_id": sector.id},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["day_of_week"] == "FRIDAY"
    assert body["sector_id"] == sector.id
    assert body["sector_name"] == "Sushi"


def test_cannot_edit_assignment_to_sector_of_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_sector
):
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_a = make_user(email="gestor-a-ta-edit@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    task_a = make_task(store_id=store_a.id, created_by_user_id=manager_a.id)
    assignment_a = make_task_assignment(task=task_a, day_of_week="MONDAY")
    sector_b = make_sector(store_id=store_b.id)
    headers = auth_headers("gestor-a-ta-edit@kijapa.com", PASSWORD)

    response = client.patch(
        f"{ASSIGNMENTS_URL}/{assignment_a.id}", json={"sector_id": sector_b.id}, headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_filter_assignments_by_sector(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_sector
):
    store = make_store()
    manager = make_user(email="gestor-ta8b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    sector_a = make_sector(store_id=store.id, name="A")
    sector_b = make_sector(store_id=store.id, name="B")
    make_task_assignment(task=task, day_of_week="MONDAY", sector_id=sector_a.id)
    make_task_assignment(task=task, day_of_week="TUESDAY", sector_id=sector_b.id)
    headers = auth_headers("gestor-ta8b@kijapa.com", PASSWORD)

    response = client.get(f"{ASSIGNMENTS_URL}?sector_id={sector_a.id}", headers=headers)

    assignments = response.json()
    assert len(assignments) == 1
    assert assignments[0]["sector_id"] == sector_a.id


def test_assignment_exposes_its_own_shift(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta8c@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    make_task_assignment(task=task, day_of_week="MONDAY", shift="Tarde")
    headers = auth_headers("gestor-ta8c@kijapa.com", PASSWORD)

    response = client.get(f"{ASSIGNMENTS_URL}?day_of_week=MONDAY", headers=headers)

    assignments = response.json()
    assert len(assignments) == 1
    assert assignments[0]["shift"] == "Tarde"


def test_same_task_can_be_assigned_to_different_shifts(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta8e@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Limpeza")
    make_task_assignment(task=task, day_of_week="MONDAY", shift="Manhã")
    make_task_assignment(task=task, day_of_week="TUESDAY", shift="Noite")
    headers = auth_headers("gestor-ta8e@kijapa.com", PASSWORD)

    response = client.get(ASSIGNMENTS_URL, headers=headers)

    shifts = {assignment["shift"] for assignment in response.json()}
    assert shifts == {"Manhã", "Noite"}


def test_filter_assignments_by_shift(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta8d@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    morning_task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Abertura")
    night_task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Fechamento")
    make_task_assignment(task=morning_task, day_of_week="MONDAY", shift="Manhã")
    make_task_assignment(task=night_task, day_of_week="MONDAY", shift="Noite")
    headers = auth_headers("gestor-ta8d@kijapa.com", PASSWORD)

    response = client.get(f"{ASSIGNMENTS_URL}?shift=Manh%C3%A3", headers=headers)

    assignments = response.json()
    assert len(assignments) == 1
    assert assignments[0]["shift"] == "Manhã"


def test_gestor_updates_assignment_shift(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta8f@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week="MONDAY", shift="Manhã")
    headers = auth_headers("gestor-ta8f@kijapa.com", PASSWORD)

    response = client.patch(f"{ASSIGNMENTS_URL}/{assignment.id}", json={"shift": "Noite"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["shift"] == "Noite"


def test_gestor_deletes_assignment(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta9@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week="MONDAY")
    headers = auth_headers("gestor-ta9@kijapa.com", PASSWORD)

    delete_response = client.delete(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_operacional_cannot_edit_or_delete_assignment(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta10@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week="MONDAY")
    make_user(email="op-ta-edit@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-edit@kijapa.com", PASSWORD)

    patch_response = client.patch(f"{ASSIGNMENTS_URL}/{assignment.id}", json={"day_of_week": "FRIDAY"}, headers=headers)
    delete_response = client.delete(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)

    assert patch_response.status_code == status.HTTP_403_FORBIDDEN
    assert delete_response.status_code == status.HTTP_403_FORBIDDEN


# --- fluxo operacional (PIN) — iniciar/concluir -------------------------------------


def test_operational_assignment_start_and_complete_via_pin(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta11@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Lavar louça")
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    make_user(email="op-ta-flow@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-flow@kijapa.com", PASSWORD)

    start_response = client.post(
        _start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers
    )
    assert start_response.status_code == status.HTTP_200_OK
    body = start_response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["started_by_employee_id"] == employee.id
    assert body["elapsed_seconds"] is not None and body["elapsed_seconds"] >= 0
    assert [p["employee_id"] for p in body["active_participants"]] == [employee.id]

    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "FEITO", "observation": "Tudo certo."},
        headers=headers,
    )
    assert complete_response.status_code == status.HTTP_200_OK
    body = complete_response.json()
    assert body["status"] == "COMPLETED"
    assert body["result"] == "FEITO"
    assert body["observation"] == "Tudo certo."
    assert body["active_participants"] == []


def test_completing_assignment_creates_execution_history_row(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment, db_session
):
    store = make_store()
    manager = make_user(email="gestor-ta21@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(
        store_id=store.id, created_by_user_id=manager.id, title="Lavar louça", estimated_duration_minutes=30
    )
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    make_user(email="op-ta-history@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-history@kijapa.com", PASSWORD)

    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)
    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "FEITO"},
        headers=headers,
    )
    assert complete_response.status_code == status.HTTP_200_OK

    history = db_session.scalars(select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)).one()
    assert history.store_id == store.id
    assert history.employee_id == employee.id
    assert history.task_title == "Lavar louça"
    assert history.result == "FEITO"
    assert history.estimated_duration_minutes == 30
    assert history.started_at is not None
    assert history.completed_at is not None
    assert history.worked_duration_seconds is not None and history.worked_duration_seconds >= 0


def test_completing_assignment_without_sla_snapshots_null_estimated_duration(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment, db_session
):
    store = make_store()
    manager = make_user(email="gestor-ta22@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)  # sem SLA configurado
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    make_user(email="op-ta-history2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-history2@kijapa.com", PASSWORD)

    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)
    client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "FEITO"},
        headers=headers,
    )

    history = db_session.scalars(select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)).one()
    assert history.estimated_duration_minutes is None


def test_employee_from_another_sector_cannot_start_assignment(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment, make_sector
):
    store = make_store()
    manager = make_user(email="gestor-ta-outsector@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task_sector = make_sector(store_id=store.id, name="Setor da Tarefa")
    other_sector = make_sector(store_id=store.id, name="Outro Setor")
    employee = make_employee(store_id=store.id, pin="1234", sector_id=other_sector.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=task_sector.id)
    make_user(email="op-ta-outsector@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-outsector@kijapa.com", PASSWORD)

    response = client.post(
        _start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_IN_SECTOR"


def test_complete_as_nao_feito_without_justification_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta13@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    make_user(email="op-ta-naofeito@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-naofeito@kijapa.com", PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "NAO_FEITO"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_complete_as_nao_feito_with_justification_and_optional_observation(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta14@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    make_user(email="op-ta-naofeito2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-naofeito2@kijapa.com", PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _complete_url(assignment.id),
        json={
            "employee_id": employee.id,
            "pin": "1234",
            "result": "NAO_FEITO",
            "justification": "Faltou insumo.",
            "observation": "Fornecedor avisado.",
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["result"] == "NAO_FEITO"
    assert body["justification"] == "Faltou insumo."
    assert body["observation"] == "Fornecedor avisado."


def test_starting_already_started_assignment_fails(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta15@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee_a = make_employee(store_id=store.id, name="A", pin="1111")
    employee_b = make_employee(store_id=store.id, name="B", pin="2222")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee_a.sector_id)
    make_user(email="op-ta-race@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-race@kijapa.com", PASSWORD)

    first = client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    assert first.status_code == status.HTTP_200_OK

    second = client.post(_start_url(assignment.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)
    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.json()["code"] == "TASK_NOT_PENDING"


# --- trava de tarefa simultânea -----------------------------------------------------


def test_employee_cannot_start_second_task_while_one_is_in_progress(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta16@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task1 = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa 1")
    task2 = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa 2")
    assignment1 = make_task_assignment(task=task1, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    assignment2 = make_task_assignment(task=task2, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    make_user(email="op-ta-lock@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-lock@kijapa.com", PASSWORD)

    first = client.post(_start_url(assignment1.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)
    assert first.status_code == status.HTTP_200_OK

    second = client.post(_start_url(assignment2.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)
    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.json()["code"] == "EMPLOYEE_HAS_ACTIVE_TASK"

    # Depois de concluir a primeira, a segunda pode ser iniciada normalmente.
    complete = client.post(
        _complete_url(assignment1.id), json={"employee_id": employee.id, "pin": "1234", "result": "FEITO"}, headers=headers
    )
    assert complete.status_code == status.HTTP_200_OK

    retry = client.post(_start_url(assignment2.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)
    assert retry.status_code == status.HTTP_200_OK


def test_different_employees_can_have_tasks_in_progress_at_the_same_time(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta17@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee_a = make_employee(store_id=store.id, name="A", pin="1111")
    employee_b = make_employee(store_id=store.id, name="B", pin="2222")
    task1 = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa 1")
    task2 = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa 2")
    assignment1 = make_task_assignment(task=task1, day_of_week=_today_day_of_week(), sector_id=employee_a.sector_id)
    assignment2 = make_task_assignment(task=task2, day_of_week=_today_day_of_week(), sector_id=employee_b.sector_id)
    make_user(email="op-ta-multi@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-multi@kijapa.com", PASSWORD)

    first = client.post(_start_url(assignment1.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)
    second = client.post(_start_url(assignment2.id), json={"employee_id": employee_b.id, "pin": "2222"}, headers=headers)

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK


# --- reset semanal automático --------------------------------------------------------


def test_completed_assignment_resets_to_pending_after_a_week(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta18@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    stale = datetime.now(timezone.utc) - timedelta(days=8)
    assignment = make_task_assignment(
        task=task,
        day_of_week=_today_day_of_week(),
        sector_id=employee.sector_id,
        status="COMPLETED",
        started_at=stale,
        completed_at=stale,
        started_by_employee_id=employee.id,
        completed_by_employee_id=employee.id,
        result="FEITO",
    )
    make_user(email="op-ta-reset@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-reset@kijapa.com", PASSWORD)

    response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["result"] is None
    assert body["started_by_employee_id"] is None
    assert body["completed_at"] is None


def test_recently_completed_assignment_does_not_reset(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta19@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    assignment = make_task_assignment(
        task=task,
        day_of_week=_today_day_of_week(),
        sector_id=employee.sector_id,
        status="COMPLETED",
        started_at=recent,
        completed_at=recent,
        started_by_employee_id=employee.id,
        completed_by_employee_id=employee.id,
        result="FEITO",
    )
    make_user(email="op-ta-noreset@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-noreset@kijapa.com", PASSWORD)

    response = client.get(f"{ASSIGNMENTS_URL}/{assignment.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "COMPLETED"


def test_stale_in_progress_assignment_resets_and_can_be_started_again(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
):
    store = make_store()
    manager = make_user(email="gestor-ta20@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    stale = datetime.now(timezone.utc) - timedelta(days=8)
    assignment = make_task_assignment(
        task=task,
        day_of_week=_today_day_of_week(),
        sector_id=employee.sector_id,
        status="IN_PROGRESS",
        started_at=stale,
        started_by_employee_id=employee.id,
    )
    make_user(email="op-ta-stale@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ta-stale@kijapa.com", PASSWORD)

    response = client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "IN_PROGRESS"
