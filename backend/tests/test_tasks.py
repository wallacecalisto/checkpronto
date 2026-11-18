
from fastapi import status
from fastapi.testclient import TestClient

TASKS_URL = "/api/v1/tasks"
PASSWORD = "SenhaForte123!"


def test_gestor_creates_task_in_own_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-task1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-task1@kijapa.com", PASSWORD)

    response = client.post(TASKS_URL, json={"title": "Fazer 150 filadélfias"}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["store_id"] == store.id
    assert body["active"] is True


def test_operacional_cannot_create_task(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="op-task-create@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-task-create@kijapa.com", PASSWORD)

    response = client.post(TASKS_URL, json={"title": "X"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_master_must_specify_store_to_create_task(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master-task1@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-task1@kijapa.com", PASSWORD)

    response = client.post(TASKS_URL, json={"title": "X"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "STORE_ID_REQUIRED"


def test_gestor_cannot_view_task_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_task
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-b-task@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id, title="Da Loja B")
    make_user(email="gestor-a-task@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-a-task@kijapa.com", PASSWORD)

    response = client.get(f"{TASKS_URL}/{task_b.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_unknown_task_returns_404(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-task404@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-task404@kijapa.com", PASSWORD)

    response = client.get(f"{TASKS_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_gestor_edits_and_deactivates_task(
    client: TestClient, make_user, auth_headers, make_store, make_task
) -> None:
    store = make_store()
    manager = make_user(email="gestor-task-edit@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Título Antigo")
    headers = auth_headers("gestor-task-edit@kijapa.com", PASSWORD)

    response = client.patch(
        f"{TASKS_URL}/{task.id}", json={"title": "Título Novo", "active": False}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["title"] == "Título Novo"
    assert body["active"] is False


def test_operacional_cannot_edit_task(client: TestClient, make_user, auth_headers, make_store, make_task) -> None:
    store = make_store()
    manager = make_user(email="gestor-task-edit2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    make_user(email="op-task-edit@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-task-edit@kijapa.com", PASSWORD)

    response = client.patch(f"{TASKS_URL}/{task.id}", json={"title": "Tentativa"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_gestor_cannot_edit_task_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_task
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-b-task2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id)
    make_user(email="gestor-a-task2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-a-task2@kijapa.com", PASSWORD)

    response = client.patch(f"{TASKS_URL}/{task_b.id}", json={"title": "Tentativa"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_gestor_creates_task_with_estimated_duration_minutes(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="gestor-task-sla1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-task-sla1@kijapa.com", PASSWORD)

    response = client.post(
        TASKS_URL,
        json={"title": "Fazer 150 filadélfias", "estimated_duration_minutes": 45},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["estimated_duration_minutes"] == 45


def test_gestor_updates_task_estimated_duration_minutes(
    client: TestClient, make_user, auth_headers, make_store, make_task
) -> None:
    store = make_store()
    manager = make_user(email="gestor-task-sla2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-task-sla2@kijapa.com", PASSWORD)

    response = client.patch(f"{TASKS_URL}/{task.id}", json={"estimated_duration_minutes": 15}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["estimated_duration_minutes"] == 15


def test_active_only_filter(client: TestClient, make_user, auth_headers, make_store, make_task) -> None:
    store = make_store()
    manager = make_user(email="gestor-task-active@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_task(store_id=store.id, created_by_user_id=manager.id, title="Ativa", active=True)
    make_task(store_id=store.id, created_by_user_id=manager.id, title="Inativa", active=False)
    headers = auth_headers("gestor-task-active@kijapa.com", PASSWORD)

    response = client.get(f"{TASKS_URL}?active_only=true", headers=headers)

    titles = {task["title"] for task in response.json()}
    assert titles == {"Ativa"}


# --- DELETE /tasks/{id} ---------------------------------


def test_master_deletes_task(client: TestClient, make_user, auth_headers, make_store, make_task) -> None:
    store = make_store()
    manager = make_user(email="gestor-task-delete1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_user(email="master-task-delete1@kijapa.com", password=PASSWORD, role="MASTER")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Vai ser excluída")
    headers = auth_headers("master-task-delete1@kijapa.com", PASSWORD)

    response = client.delete(f"{TASKS_URL}/{task.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False

    entries = client.get("/api/v1/audit", headers=headers).json()
    actions = {entry["action"] for entry in entries if entry["entity_id"] == task.id and entry["entity_type"] == "TASK"}
    assert "DELETE" in actions


def test_gestor_cannot_delete_task(client: TestClient, make_user, auth_headers, make_store, make_task) -> None:
    store = make_store()
    manager = make_user(email="gestor-task-delete2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-task-delete2@kijapa.com", PASSWORD)

    response = client.delete(f"{TASKS_URL}/{task.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_lider_cannot_delete_task(client: TestClient, make_user, auth_headers, make_store, make_task) -> None:
    store = make_store()
    manager = make_user(email="gestor-task-delete3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_user(email="lider-task-delete@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("lider-task-delete@kijapa.com", PASSWORD)

    response = client.delete(f"{TASKS_URL}/{task.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_unknown_task_returns_404(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master-task-delete2@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-task-delete2@kijapa.com", PASSWORD)

    response = client.delete(f"{TASKS_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_deleting_already_inactive_task_is_idempotent(
    client: TestClient, make_user, auth_headers, make_store, make_task
) -> None:
    store = make_store()
    manager = make_user(email="gestor-task-delete4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_user(email="master-task-delete3@kijapa.com", password=PASSWORD, role="MASTER")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, active=False)
    headers = auth_headers("master-task-delete3@kijapa.com", PASSWORD)

    response = client.delete(f"{TASKS_URL}/{task.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False
    entries = client.get("/api/v1/audit", headers=headers).json()
    delete_logs = [
        entry for entry in entries if entry["entity_id"] == task.id and entry["entity_type"] == "TASK" and entry["action"] == "DELETE"
    ]
    assert len(delete_logs) == 0
