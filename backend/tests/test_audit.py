
from datetime import datetime, timedelta, timezone

from fastapi import status
from fastapi.testclient import TestClient

AUDIT_URL = "/api/v1/audit"
PASSWORD = "SenhaForte123!"


def _last_entry(client: TestClient, headers: dict) -> dict:
    response = client.get(AUDIT_URL, headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    entries = response.json()
    assert entries, "esperava pelo menos um registro de auditoria"
    return entries[0]  # GET /audit ordena do mais recente para o mais antigo


# --- funcionários -----------------------------------------------------------------


def test_creating_employee_generates_audit_log(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="gestor-au1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id, name="Gestora Ana")
    headers = auth_headers("gestor-au1@kijapa.com", PASSWORD)

    response = client.post(
        "/api/v1/employees", json={"name": "Novo Funcionário", "sector_id": sector.id}, headers=headers
    )
    employee_id = response.json()["id"]

    entry = _last_entry(client, headers)
    assert entry["action"] == "CREATE"
    assert entry["entity_type"] == "EMPLOYEE"
    assert entry["entity_id"] == employee_id
    assert entry["actor_type"] == "USER"
    assert entry["actor_name"] == "Gestora Ana"
    assert entry["before_data"] is None
    assert entry["after_data"]["name"] == "Novo Funcionário"


def test_updating_employee_name_generates_update_with_before_after(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    make_user(email="gestor-au2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Nome Antigo")
    headers = auth_headers("gestor-au2@kijapa.com", PASSWORD)

    client.patch(f"/api/v1/employees/{employee.id}", json={"name": "Nome Novo"}, headers=headers)

    entry = _last_entry(client, headers)
    assert entry["action"] == "UPDATE"
    assert entry["before_data"]["name"] == "Nome Antigo"
    assert entry["after_data"]["name"] == "Nome Novo"


def test_deactivating_and_reactivating_employee_generates_distinct_actions(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    make_user(email="gestor-au3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    headers = auth_headers("gestor-au3@kijapa.com", PASSWORD)

    client.patch(f"/api/v1/employees/{employee.id}", json={"active": False}, headers=headers)
    deactivated_entry = _last_entry(client, headers)
    assert deactivated_entry["action"] == "DEACTIVATE"

    client.patch(f"/api/v1/employees/{employee.id}", json={"active": True}, headers=headers)
    reactivated_entry = _last_entry(client, headers)
    assert reactivated_entry["action"] == "ACTIVATE"


def test_resetting_employee_pin_generates_audit_log(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    make_user(email="gestor-au19@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, pin="1234")
    headers = auth_headers("gestor-au19@kijapa.com", PASSWORD)

    response = client.post(f"/api/v1/employees/{employee.id}/pin/reset", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["has_pin"] is False

    entry = _last_entry(client, headers)
    assert entry["action"] == "RESET_PIN"
    assert entry["entity_type"] == "EMPLOYEE"
    assert entry["entity_id"] == employee.id


# --- tarefas -----------------------------------------------------------------------


def test_creating_task_generates_audit_log(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-au4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-au4@kijapa.com", PASSWORD)

    response = client.post(
        "/api/v1/tasks", json={"title": "Fazer 150 filadélfias", "shift": "Geral"}, headers=headers
    )
    task_id = response.json()["id"]

    entry = _last_entry(client, headers)
    assert entry["action"] == "CREATE"
    assert entry["entity_type"] == "TASK"
    assert entry["entity_id"] == task_id
    assert entry["after_data"]["title"] == "Fazer 150 filadélfias"


def test_editing_task_title_generates_update(
    client: TestClient, make_user, auth_headers, make_store, make_task
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Antigo")
    headers = auth_headers("gestor-au5@kijapa.com", PASSWORD)

    client.patch(f"/api/v1/tasks/{task.id}", json={"title": "Novo"}, headers=headers)

    entry = _last_entry(client, headers)
    assert entry["action"] == "UPDATE"
    assert entry["entity_type"] == "TASK"
    assert entry["before_data"]["title"] == "Antigo"
    assert entry["after_data"]["title"] == "Novo"


# --- agendamentos (TaskAssignment) --------------------------------------------------


def test_creating_task_assignment_generates_audit_log(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_sector
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au16@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    sector = make_sector(store_id=store.id)
    headers = auth_headers("gestor-au16@kijapa.com", PASSWORD)

    response = client.post(
        "/api/v1/task-assignments",
        json={"task_id": task.id, "day_of_week": "MONDAY", "sector_id": sector.id, "shift": "Geral"},
        headers=headers,
    )
    assignment_id = response.json()["id"]

    entry = _last_entry(client, headers)
    assert entry["action"] == "CREATE"
    assert entry["entity_type"] == "TASK_ASSIGNMENT"
    assert entry["entity_id"] == assignment_id
    assert entry["after_data"]["sector_id"] == sector.id


def test_editing_task_assignment_generates_update_audit_log(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_sector
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au17@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week="MONDAY")
    sector = make_sector(store_id=store.id)
    headers = auth_headers("gestor-au17@kijapa.com", PASSWORD)

    client.patch(
        f"/api/v1/task-assignments/{assignment.id}",
        json={"day_of_week": "FRIDAY", "sector_id": sector.id},
        headers=headers,
    )

    entry = _last_entry(client, headers)
    assert entry["action"] == "UPDATE"
    assert entry["entity_type"] == "TASK_ASSIGNMENT"
    assert entry["before_data"]["day_of_week"] == "MONDAY"
    assert entry["after_data"]["day_of_week"] == "FRIDAY"


def test_deleting_task_assignment_generates_delete_audit_log(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au18@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    assignment = make_task_assignment(task=task, day_of_week="MONDAY")
    headers = auth_headers("gestor-au18@kijapa.com", PASSWORD)

    client.delete(f"/api/v1/task-assignments/{assignment.id}", headers=headers)

    entry = _last_entry(client, headers)
    assert entry["action"] == "DELETE"
    assert entry["entity_type"] == "TASK_ASSIGNMENT"
    assert entry["entity_id"] == assignment.id


# --- templates de checklist ----------------------------------------------------------


def test_creating_checklist_template_with_items_generates_audit_log(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="gestor-au6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-au6@kijapa.com", PASSWORD)

    response = client.post(
        "/api/v1/checklist-templates",
        json={"name": "Fechamento", "shift": "Geral", "items": [{"description": "Desligar a fritadeira"}]},
        headers=headers,
    )
    template_id = response.json()["id"]

    entry = _last_entry(client, headers)
    assert entry["action"] == "CREATE"
    assert entry["entity_type"] == "CHECKLIST_TEMPLATE"
    assert entry["entity_id"] == template_id
    assert entry["after_data"]["name"] == "Fechamento"
    assert entry["after_data"]["items"][0]["description"] == "Desligar a fritadeira"


def test_adding_and_editing_template_item_generates_audit_logs(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au7@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-au7@kijapa.com", PASSWORD)

    item_response = client.post(
        f"/api/v1/checklist-templates/{template.id}/items", json={"description": "Item novo"}, headers=headers
    )
    item_id = item_response.json()["id"]

    create_entry = _last_entry(client, headers)
    assert create_entry["action"] == "CREATE"
    assert create_entry["entity_type"] == "CHECKLIST_TEMPLATE_ITEM"
    assert create_entry["entity_id"] == item_id

    client.patch(f"/api/v1/checklist-template-items/{item_id}", json={"description": "Item editado"}, headers=headers)
    update_entry = _last_entry(client, headers)
    assert update_entry["action"] == "UPDATE"
    assert update_entry["before_data"]["description"] == "Item novo"
    assert update_entry["after_data"]["description"] == "Item editado"


# --- execuções e validações cruzadas de checklist -------------------------------------


def test_starting_checklist_as_manager_generates_start_with_user_actor(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au8@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    headers = auth_headers("gestor-au8@kijapa.com", PASSWORD)

    response = client.post("/api/v1/checklists", json={"template_id": template.id, "shift": "MANHA"}, headers=headers)
    execution_id = response.json()["id"]

    entry = _last_entry(client, headers)
    assert entry["action"] == "START"
    assert entry["entity_type"] == "CHECKLIST_EXECUTION"
    assert entry["entity_id"] == execution_id
    assert entry["actor_type"] == "USER"
    assert entry["actor_user_id"] == manager.id


def test_completing_checklist_generates_complete_attributed_to_starter(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au10@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, required=False)
    headers = auth_headers("gestor-au10@kijapa.com", PASSWORD)

    execution = client.post(
        "/api/v1/checklists", json={"template_id": template.id, "shift": "NOITE"}, headers=headers
    ).json()
    client.post(f"/api/v1/checklists/{execution['id']}/complete", headers=headers)

    entry = _last_entry(client, headers)
    assert entry["action"] == "COMPLETE"
    assert entry["entity_type"] == "CHECKLIST_EXECUTION"
    assert entry["actor_user_id"] == manager.id
    assert entry["after_data"]["status"] == "COMPLETED"


def test_validating_item_generates_validate_audit_log(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au11@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    headers = auth_headers("gestor-au11@kijapa.com", PASSWORD)

    execution = client.post(
        "/api/v1/checklists", json={"template_id": template.id, "shift": "MANHA"}, headers=headers
    ).json()
    item_id = execution["items"][0]["id"]
    client.patch(f"/api/v1/checklists/{execution['id']}/items/{item_id}", json={"response": "OK"}, headers=headers)
    client.post(f"/api/v1/checklists/{execution['id']}/complete", headers=headers)

    lider = make_user(email="lider-au11@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id, name="Lider Carlos")
    lider_headers = auth_headers("lider-au11@kijapa.com", PASSWORD)
    validate_response = client.post(
        f"/api/v1/checklists/{execution['id']}/items/{item_id}/validate",
        json={"result": "APROVADO"},
        headers=lider_headers,
    )
    validation_id = validate_response.json()["id"]

    entry = _last_entry(client, headers)
    assert entry["action"] == "VALIDATE"
    assert entry["entity_type"] == "CHECKLIST_VALIDATION"
    assert entry["entity_id"] == validation_id
    assert entry["actor_user_id"] == lider.id
    assert entry["actor_name"] == "Lider Carlos"


# --- acesso e filtros de GET /audit ----------------------------------------------------


def test_operacional_and_lider_cannot_access_audit(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="op-au12@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    make_user(email="lider-au12@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)

    op_response = client.get(AUDIT_URL, headers=auth_headers("op-au12@kijapa.com", PASSWORD))
    lider_response = client.get(AUDIT_URL, headers=auth_headers("lider-au12@kijapa.com", PASSWORD))

    assert op_response.status_code == status.HTTP_403_FORBIDDEN
    assert lider_response.status_code == status.HTTP_403_FORBIDDEN


def test_gestor_only_sees_own_store_logs(
    client: TestClient, make_user, auth_headers, make_store, make_audit_log
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_a = make_user(email="gestor-a-au@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    make_user(email="gestor-b-au@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    make_audit_log(
        store_id=store_a.id, action="CREATE", entity_type="EMPLOYEE", entity_id=1,
        actor_user_id=manager_a.id, actor_name="Gestor A",
    )
    make_audit_log(
        store_id=store_b.id, action="CREATE", entity_type="EMPLOYEE", entity_id=2,
        actor_user_id=manager_a.id, actor_name="Gestor A",
    )
    headers_a = auth_headers("gestor-a-au@kijapa.com", PASSWORD)

    response = client.get(AUDIT_URL, headers=headers_a)

    entries = response.json()
    assert all(entry["store_id"] == store_a.id for entry in entries)


def test_master_sees_all_stores_and_can_filter_by_store(
    client: TestClient, make_user, auth_headers, make_store, make_audit_log
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    master = make_user(email="master-au@kijapa.com", password=PASSWORD, role="MASTER")
    make_audit_log(
        store_id=store_a.id, action="CREATE", entity_type="EMPLOYEE", entity_id=1,
        actor_user_id=master.id, actor_name="Alguém",
    )
    make_audit_log(
        store_id=store_b.id, action="CREATE", entity_type="EMPLOYEE", entity_id=2,
        actor_user_id=master.id, actor_name="Alguém",
    )
    headers = auth_headers("master-au@kijapa.com", PASSWORD)

    all_entries = client.get(AUDIT_URL, headers=headers).json()
    assert len(all_entries) >= 2

    filtered = client.get(f"{AUDIT_URL}?store_id={store_a.id}", headers=headers).json()
    assert all(entry["store_id"] == store_a.id for entry in filtered)


def test_filters_by_action_entity_type_and_actor(
    client: TestClient, make_user, auth_headers, make_store, make_audit_log
) -> None:
    store = make_store()
    manager = make_user(email="gestor-au13@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_audit_log(
        store_id=store.id, action="CREATE", entity_type="TASK", entity_id=1,
        actor_user_id=manager.id, actor_name="Gestora",
    )
    make_audit_log(
        store_id=store.id, action="DEACTIVATE", entity_type="EMPLOYEE", entity_id=2,
        actor_user_id=manager.id, actor_name="Gestora",
    )
    headers = auth_headers("gestor-au13@kijapa.com", PASSWORD)

    by_action = client.get(f"{AUDIT_URL}?action=DEACTIVATE", headers=headers).json()
    assert all(entry["action"] == "DEACTIVATE" for entry in by_action)
    assert any(entry["entity_type"] == "EMPLOYEE" for entry in by_action)

    by_entity_type = client.get(f"{AUDIT_URL}?entity_type=TASK", headers=headers).json()
    assert all(entry["entity_type"] == "TASK" for entry in by_entity_type)

    by_actor = client.get(f"{AUDIT_URL}?actor_user_id={manager.id}", headers=headers).json()
    assert len(by_actor) >= 2


def test_filters_by_date_range(client: TestClient, make_user, auth_headers, make_store, make_audit_log) -> None:
    store = make_store()
    manager = make_user(email="gestor-au14@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    today = datetime.now(timezone.utc)
    make_audit_log(
        store_id=store.id, action="CREATE", entity_type="TASK", entity_id=1,
        actor_user_id=manager.id, actor_name="Gestora", created_at=today - timedelta(days=10),
    )
    make_audit_log(
        store_id=store.id, action="CREATE", entity_type="TASK", entity_id=2,
        actor_user_id=manager.id, actor_name="Gestora", created_at=today,
    )
    headers = auth_headers("gestor-au14@kijapa.com", PASSWORD)

    date_from = (today - timedelta(days=1)).date().isoformat()
    response = client.get(f"{AUDIT_URL}?date_from={date_from}", headers=headers)

    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["entity_id"] == 2


def test_actor_name_is_a_snapshot_and_does_not_change_if_actor_is_renamed(
    client: TestClient, make_user, auth_headers, make_store, make_sector, db_session
) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    manager = make_user(
        email="gestor-au15@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id, name="Nome Original"
    )
    headers = auth_headers("gestor-au15@kijapa.com", PASSWORD)

    client.post("/api/v1/employees", json={"name": "Alguém", "sector_id": sector.id}, headers=headers)
    entry_before_rename = _last_entry(client, headers)
    assert entry_before_rename["actor_name"] == "Nome Original"

    # Não existe endpoint para o próprio usuário se renomear — muda direto no
    # banco só para provar que o log não faz JOIN ao vivo (é um snapshot).
    manager.name = "Nome Renomeado"
    db_session.add(manager)
    db_session.commit()

    entry_after_rename = _last_entry(client, headers)
    assert entry_after_rename["actor_name"] == "Nome Original"
