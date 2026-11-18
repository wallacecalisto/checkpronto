
from datetime import datetime, timezone

from fastapi import status
from fastapi.testclient import TestClient

from app.models.task import DAYS_OF_WEEK

CHECKLISTS_URL = "/api/v1/checklists"
TEMPLATES_URL = "/api/v1/checklist-templates"
PASSWORD = "SenhaForte123!"


def _item_url(execution_id: int, item_id: int) -> str:
    return f"{CHECKLISTS_URL}/{execution_id}/items/{item_id}"


def _complete_url(execution_id: int) -> str:
    return f"{CHECKLISTS_URL}/{execution_id}/complete"


def _validate_url(execution_id: int, item_id: int) -> str:
    return f"{CHECKLISTS_URL}/{execution_id}/items/{item_id}/validate"


# --- iniciar via PIN -----------------------------------------------------------------


def test_employee_starts_execution_via_pin(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Carlos", pin="1234")
    template = make_checklist_template(
        store_id=store.id, created_by_user_id=manager.id, target_sector_id=employee.sector_id
    )
    make_checklist_template_item(template=template, description="Desligar a fritadeira")
    make_user(email="op-clpin1@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin1@kijapa.com", PASSWORD)

    response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA", "employee_id": employee.id, "pin": "1234"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["executed_by_employee_id"] == employee.id
    assert body["executed_by_user_id"] is None
    assert body["executed_by_name"] == "Carlos"


def test_employee_can_start_a_management_checklist_without_sector(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)  # sem setor
    make_checklist_template_item(template=template)
    make_user(email="op-clpin2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin2@kijapa.com", PASSWORD)

    response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA", "employee_id": employee.id, "pin": "1234"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_employee_from_another_sector_cannot_start_execution(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_sector, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template_sector = make_sector(store_id=store.id, name="Cozinha Quente")
    other_sector = make_sector(store_id=store.id, name="Sushi")
    employee = make_employee(store_id=store.id, pin="1234", sector_id=other_sector.id)
    template = make_checklist_template(
        store_id=store.id, created_by_user_id=manager.id, target_sector_id=template_sector.id
    )
    make_checklist_template_item(template=template)
    make_user(email="op-clpin3@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin3@kijapa.com", PASSWORD)

    response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA", "employee_id": employee.id, "pin": "1234"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_NOT_IN_SECTOR"


def test_inactive_employee_cannot_start_execution(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234", active=False)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    make_user(email="op-clpin4@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin4@kijapa.com", PASSWORD)

    response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA", "employee_id": employee.id, "pin": "1234"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_INACTIVE"


def test_checklists_disabled_for_store_blocks_starting_via_pin(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin4b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    manager_headers = auth_headers("gestor-clpin4b@kijapa.com", PASSWORD)
    client.patch(
        f"/api/v1/stores/{store.id}/settings", json={"operational_checklists_enabled": False}, headers=manager_headers
    )
    make_user(email="op-clpin4b@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin4b@kijapa.com", PASSWORD)

    response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA", "employee_id": employee.id, "pin": "1234"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "CHECKLISTS_DISABLED_FOR_STORE"


def test_checklists_disabled_for_store_does_not_affect_manager_started_executions(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin4c@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    manager_headers = auth_headers("gestor-clpin4c@kijapa.com", PASSWORD)
    client.patch(
        f"/api/v1/stores/{store.id}/settings", json={"operational_checklists_enabled": False}, headers=manager_headers
    )

    response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA"},
        headers=manager_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_employee_can_start_a_checklist_while_in_an_active_task(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_employee,
    make_task,
    make_task_assignment,
    make_checklist_template,
    make_checklist_template_item,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin4d@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    today = DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]
    assignment = make_task_assignment(task=task, day_of_week=today, sector_id=employee.sector_id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    make_user(email="op-clpin4d@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin4d@kijapa.com", PASSWORD)

    start_task_response = client.post(
        f"/api/v1/task-assignments/{assignment.id}/start", json={"employee_id": employee.id, "pin": "1234"}, headers=headers
    )
    assert start_task_response.status_code == status.HTTP_200_OK

    response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA", "employee_id": employee.id, "pin": "1234"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_wrong_pin_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    make_user(email="op-clpin5@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin5@kijapa.com", PASSWORD)

    response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA", "employee_id": employee.id, "pin": "9999"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "PIN_INCORRECT"


def test_full_flow_employee_answers_and_manager_validates(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    lider = make_user(email="lider-clpin6@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    item = make_checklist_template_item(template=template, description="Desligar a fritadeira")
    make_user(email="op-clpin6@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    op_headers = auth_headers("op-clpin6@kijapa.com", PASSWORD)

    start_response = client.post(
        CHECKLISTS_URL,
        json={"template_id": template.id, "shift": "MANHA", "employee_id": employee.id, "pin": "1234"},
        headers=op_headers,
    )
    execution_id = start_response.json()["id"]
    execution_item_id = start_response.json()["items"][0]["id"]

    # Responder um item NÃO reverifica o PIN — mesma sessão de loja já
    # autenticada ao iniciar (mesmo padrão já usado pra checklists de gestão).
    answer_response = client.patch(
        _item_url(execution_id, execution_item_id), json={"response": "OK"}, headers=op_headers
    )
    assert answer_response.status_code == status.HTTP_200_OK

    complete_response = client.post(_complete_url(execution_id), headers=op_headers)
    assert complete_response.status_code == status.HTTP_200_OK
    assert complete_response.json()["status"] == "COMPLETED"

    lider_headers = auth_headers("lider-clpin6@kijapa.com", PASSWORD)
    validate_response = client.post(
        _validate_url(execution_id, execution_item_id), json={"result": "APROVADO"}, headers=lider_headers
    )

    assert validate_response.status_code == status.HTTP_201_CREATED
    assert validate_response.json()["validated_by_user_id"] == lider.id


def test_operational_role_user_without_pin_still_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin7@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    make_user(email="op-clpin7@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin7@kijapa.com", PASSWORD)

    response = client.post(CHECKLISTS_URL, json={"template_id": template.id, "shift": "MANHA"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- listagem de templates filtrada por setor (tablet) ------------------------------


def test_tablet_lists_only_own_sector_and_general_templates(
    client: TestClient, make_user, auth_headers, make_store, make_employee, make_sector, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-clpin8@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sector_a = make_sector(store_id=store.id, name="Cozinha Quente")
    sector_b = make_sector(store_id=store.id, name="Sushi")
    employee = make_employee(store_id=store.id, sector_id=sector_a.id)
    make_checklist_template(
        store_id=store.id, created_by_user_id=manager.id, name="Da Cozinha", target_sector_id=sector_a.id
    )
    make_checklist_template(
        store_id=store.id, created_by_user_id=manager.id, name="Do Sushi", target_sector_id=sector_b.id
    )
    make_checklist_template(store_id=store.id, created_by_user_id=manager.id, name="Geral")
    make_user(email="op-clpin8@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-clpin8@kijapa.com", PASSWORD)

    response = client.get(f"{TEMPLATES_URL}?sector_id={employee.sector_id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    names = {template["name"] for template in response.json()}
    assert names == {"Da Cozinha", "Geral"}
