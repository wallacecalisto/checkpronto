
from datetime import datetime, timezone

from fastapi import status
from fastapi.testclient import TestClient

from app.models.task import DAYS_OF_WEEK
from app.services.pin_service import MAX_PIN_ATTEMPTS

EMPLOYEES_URL = "/api/v1/employees"
TASKS_URL = "/api/v1/tasks"
ASSIGNMENTS_URL = "/api/v1/task-assignments"
STORES_URL = "/api/v1/stores"
DASHBOARD_URL = "/api/v1/dashboard"
PASSWORD = "SenhaForte123!"


def _today_day_of_week() -> str:
    return DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]


def _start_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/start"


def _complete_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/complete"


def test_scenario_1_gestor_cannot_read_employee_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    employee_b = make_employee(store_id=store_b.id, name="Funcionário da Loja B")
    make_user(email="sec1-gestor-a@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("sec1-gestor-a@kijapa.com", PASSWORD)

    response = client.get(f"{EMPLOYEES_URL}/{employee_b.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_scenario_1_gestor_cannot_edit_task_from_another_store_by_guessing_id(
    client: TestClient, make_user, auth_headers, make_store, make_task
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="sec1-gestor-b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id)
    make_user(email="sec1-gestor-a2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("sec1-gestor-a2@kijapa.com", PASSWORD)

    # Loja A tenta editar (e depois excluir) uma tarefa que sabe existir na Loja B.
    patch_response = client.patch(f"{TASKS_URL}/{task_b.id}", json={"title": "Sequestrada"}, headers=headers)
    assert patch_response.status_code == status.HTTP_403_FORBIDDEN


def test_scenario_1_gestor_cannot_view_another_stores_record_even_guessing_sequential_ids(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    store_c = make_store(name="Loja C")
    make_user(email="sec1-gestor-a3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("sec1-gestor-a3@kijapa.com", PASSWORD)

    for other_store in (store_b, store_c):
        response = client.get(f"{STORES_URL}/{other_store.id}", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_scenario_2_operacional_cannot_access_dashboard(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="sec2-op1@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec2-op1@kijapa.com", PASSWORD)

    for path in ("/summary", "/ranking", "/weekly-trend", "/activity-feed", "/exceptions", "/recent-checklists"):
        response = client.get(DASHBOARD_URL + path, headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN, path


def test_scenario_2_operacional_cannot_manage_catalog_or_users(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="sec2-op2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec2-op2@kijapa.com", PASSWORD)

    create_task = client.post(TASKS_URL, json={"title": "Tarefa Indevida"}, headers=headers)
    create_employee = client.post(
        EMPLOYEES_URL, json={"name": "Funcionário Indevido", "sector_id": sector.id}, headers=headers
    )
    list_users = client.get("/api/v1/users", headers=headers)
    create_store = client.post(STORES_URL, json={"name": "Loja Indevida"}, headers=headers)

    assert create_task.status_code == status.HTTP_403_FORBIDDEN
    assert create_employee.status_code == status.HTTP_403_FORBIDDEN
    assert list_users.status_code == status.HTTP_403_FORBIDDEN
    assert create_store.status_code == status.HTTP_403_FORBIDDEN


def test_scenario_2_operacional_cannot_delete_from_the_master_only_catalog_endpoints(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="sec2-gestor@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_user(email="sec2-op3@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec2-op3@kijapa.com", PASSWORD)

    assert client.delete(f"{TASKS_URL}/{task.id}", headers=headers).status_code == status.HTTP_403_FORBIDDEN
    assert (
        client.delete(f"/api/v1/checklist-templates/{template.id}", headers=headers).status_code
        == status.HTTP_403_FORBIDDEN
    )


def test_scenario_3_employee_from_another_sector_cannot_start_the_task(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment, make_sector
) -> None:
    store = make_store()
    manager = make_user(email="sec3-gestor@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sector_a = make_sector(store_id=store.id, name="Setor A")
    sector_b = make_sector(store_id=store.id, name="Setor B")
    outsider = make_employee(store_id=store.id, name="De fora", pin="2222", sector_id=sector_b.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=sector_a.id)
    make_user(email="sec3-op@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec3-op@kijapa.com", PASSWORD)

    response = client.post(
        _start_url(assignment.id), json={"employee_id": outsider.id, "pin": "2222"}, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_IN_SECTOR"


def test_scenario_3_employee_from_another_sector_cannot_complete_the_task(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment, make_sector
) -> None:
    store = make_store()
    manager = make_user(email="sec3-gestor2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sector_a = make_sector(store_id=store.id, name="Setor A")
    sector_b = make_sector(store_id=store.id, name="Setor B")
    employee_a = make_employee(store_id=store.id, name="Do setor A", pin="1111", sector_id=sector_a.id)
    outsider = make_employee(store_id=store.id, name="De fora", pin="2222", sector_id=sector_b.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=sector_a.id)
    make_user(email="sec3-op2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec3-op2@kijapa.com", PASSWORD)

    # Alguém do setor certo inicia normalmente...
    client.post(_start_url(assignment.id), json={"employee_id": employee_a.id, "pin": "1111"}, headers=headers)

    # ...mas um funcionário de OUTRO setor tenta concluir no lugar dela.
    response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": outsider.id, "pin": "2222", "result": "FEITO"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_IN_SECTOR"


def test_scenario_4_operations_on_nonexistent_task_return_404(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="sec4-gestor@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("sec4-gestor@kijapa.com", PASSWORD)

    assert client.get(f"{TASKS_URL}/999999", headers=headers).status_code == status.HTTP_404_NOT_FOUND
    assert (
        client.patch(f"{TASKS_URL}/999999", json={"title": "X"}, headers=headers).status_code
        == status.HTTP_404_NOT_FOUND
    )
    assert client.delete(f"{TASKS_URL}/999999", headers=headers).status_code in (
        status.HTTP_404_NOT_FOUND,
        status.HTTP_403_FORBIDDEN,  # GESTOR não é MASTER — barrado antes mesmo do 404 (ver cenário 2)
    )


def test_scenario_4_operations_on_nonexistent_assignment_return_404(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="sec4-gestor2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    headers = auth_headers("sec4-gestor2@kijapa.com", PASSWORD)

    assert client.get(f"{ASSIGNMENTS_URL}/999999", headers=headers).status_code == status.HTTP_404_NOT_FOUND
    assert (
        client.patch(f"{ASSIGNMENTS_URL}/999999", json={"day_of_week": "FRIDAY"}, headers=headers).status_code
        == status.HTTP_404_NOT_FOUND
    )

    start_response = client.post(
        _start_url(999999), json={"employee_id": employee.id, "pin": "1234"}, headers=headers
    )
    assert start_response.status_code == status.HTTP_404_NOT_FOUND

    complete_response = client.post(
        _complete_url(999999), json={"employee_id": employee.id, "pin": "1234", "result": "FEITO"}, headers=headers
    )
    assert complete_response.status_code == status.HTTP_404_NOT_FOUND


def test_scenario_4_starting_task_for_nonexistent_employee_returns_404(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
) -> None:
    store = make_store()
    manager = make_user(email="sec4-gestor3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week())
    make_user(email="sec4-op@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec4-op@kijapa.com", PASSWORD)

    response = client.post(
        _start_url(assignment.id), json={"employee_id": 999999, "pin": "0000"}, headers=headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_scenario_5_completing_as_nao_feito_without_justification_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
) -> None:
    store = make_store()
    manager = make_user(email="sec5-gestor@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week())
    make_user(email="sec5-op@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec5-op@kijapa.com", PASSWORD)

    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "NAO_FEITO"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_scenario_5_completing_as_nao_feito_with_blank_justification_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
) -> None:
    store = make_store()
    manager = make_user(email="sec5-gestor2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week())
    make_user(email="sec5-op2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec5-op2@kijapa.com", PASSWORD)

    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "NAO_FEITO", "justification": "   "},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_scenario_5_completing_as_nao_feito_with_justification_succeeds(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
) -> None:
    store = make_store()
    manager = make_user(email="sec5-gestor3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week())
    make_user(email="sec5-op3@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec5-op3@kijapa.com", PASSWORD)

    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "NAO_FEITO", "justification": "Faltou insumo."},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"] == "NAO_FEITO"


def test_scenario_6_pin_locks_after_max_wrong_attempts_and_rejects_even_the_correct_pin(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="sec6-op@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec6-op@kijapa.com", PASSWORD)

    for _ in range(MAX_PIN_ATTEMPTS):
        response = client.post(
            f"{EMPLOYEES_URL}/{employee.id}/pin/authenticate", json={"pin": "0000"}, headers=headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["code"] == "PIN_INCORRECT"

    # Bloqueado — nem o PIN CORRETO passa agora.
    locked_response = client.post(
        f"{EMPLOYEES_URL}/{employee.id}/pin/authenticate", json={"pin": "9999"}, headers=headers
    )
    assert locked_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert locked_response.json()["code"] == "PIN_LOCKED"


def test_scenario_6_pin_lockout_is_per_employee_not_global(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    locked_employee = make_employee(store_id=store.id, pin="9999", name="Vai bloquear")
    free_employee = make_employee(store_id=store.id, pin="1234", name="Continua livre")
    make_user(email="sec6-op2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec6-op2@kijapa.com", PASSWORD)

    for _ in range(MAX_PIN_ATTEMPTS):
        client.post(f"{EMPLOYEES_URL}/{locked_employee.id}/pin/authenticate", json={"pin": "0000"}, headers=headers)

    response = client.post(
        f"{EMPLOYEES_URL}/{free_employee.id}/pin/authenticate", json={"pin": "1234"}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK


def test_scenario_7_gestor_cannot_create_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="sec7-gestor@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("sec7-gestor@kijapa.com", PASSWORD)

    response = client.post(STORES_URL, json={"name": "Loja Não Autorizada"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_scenario_7_lider_and_operacional_cannot_create_store(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="sec7-lider@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    make_user(email="sec7-op@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)

    for email in ("sec7-lider@kijapa.com", "sec7-op@kijapa.com"):
        headers = auth_headers(email, PASSWORD)
        response = client.post(STORES_URL, json={"name": "Loja Não Autorizada"}, headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN, email


def test_scenario_7_master_can_create_store(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="sec7-master@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("sec7-master@kijapa.com", PASSWORD)

    response = client.post(STORES_URL, json={"name": "Loja Nova"}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED


def test_scenario_8_inactive_employee_cannot_authenticate_pin(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999", active=False)
    make_user(email="sec8-op@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec8-op@kijapa.com", PASSWORD)

    response = client.post(f"{EMPLOYEES_URL}/{employee.id}/pin/authenticate", json={"pin": "9999"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_INACTIVE"


def test_scenario_8_inactive_sector_cannot_be_assigned_a_new_task(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_sector
) -> None:
    store = make_store()
    manager = make_user(email="sec8-gestor@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sector = make_sector(store_id=store.id, active=False)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("sec8-gestor@kijapa.com", PASSWORD)

    response = client.post(
        ASSIGNMENTS_URL,
        json={"task_id": task.id, "day_of_week": "MONDAY", "sector_id": sector.id, "shift": "Geral"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "SECTOR_INACTIVE"


def test_scenario_8_employee_deactivated_after_scheduling_cannot_start_the_task(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_task, make_task_assignment
) -> None:
    store = make_store()
    manager = make_user(email="sec8-gestor2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    make_user(email="sec8-op2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("sec8-op2@kijapa.com", PASSWORD)

    deactivate_response = client.patch(
        f"{EMPLOYEES_URL}/{employee.id}", json={"active": False}, headers=headers
    )
    assert deactivate_response.status_code == status.HTTP_403_FORBIDDEN  # OPERACIONAL não pode desativar

    # Desativa de verdade como gestor.
    gestor_headers = auth_headers("sec8-gestor2@kijapa.com", PASSWORD)
    client.patch(f"{EMPLOYEES_URL}/{employee.id}", json={"active": False}, headers=gestor_headers)

    response = client.post(
        _start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_INACTIVE"
