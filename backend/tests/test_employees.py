from fastapi import status
from fastapi.testclient import TestClient

EMPLOYEES_URL = "/api/v1/employees"
PASSWORD = "SenhaForte123!"


# --- criação -----------------------------------------------------------------


def test_gestor_creates_employee_in_own_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store(name="Loja do Gestor")
    sector = make_sector(store_id=store.id)
    make_user(email="gestor-emp@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-emp@kijapa.com", PASSWORD)

    response = client.post(
        EMPLOYEES_URL,
        json={"name": "João da Cozinha", "role_title": "Cozinheiro", "sector_id": sector.id},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["name"] == "João da Cozinha"
    assert body["store_id"] == store.id
    assert body["sector_id"] == sector.id
    assert body["active"] is True
    assert body["has_pin"] is False  # nasce sem PIN, por regra


def test_gestor_cannot_create_employee_in_another_store_by_faking_store_id(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    own_store = make_store(name="Loja A")
    other_store = make_store(name="Loja B")
    own_sector = make_sector(store_id=own_store.id)
    make_user(email="gestor-emp2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=own_store.id)
    headers = auth_headers("gestor-emp2@kijapa.com", PASSWORD)

    response = client.post(
        EMPLOYEES_URL,
        json={"name": "Tentativa", "store_id": other_store.id, "sector_id": own_sector.id},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["store_id"] == own_store.id


def test_gestor_cannot_assign_employee_to_sector_of_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    own_store = make_store(name="Loja A")
    other_store = make_store(name="Loja B")
    sector_from_other_store = make_sector(store_id=other_store.id, name="Setor de Outra Loja")
    make_user(email="gestor-emp3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=own_store.id)
    headers = auth_headers("gestor-emp3@kijapa.com", PASSWORD)

    response = client.post(
        EMPLOYEES_URL,
        json={"name": "Tentativa", "sector_id": sector_from_other_store.id},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_master_must_specify_store_id_to_create_employee(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="master-emp@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-emp@kijapa.com", PASSWORD)

    response = client.post(EMPLOYEES_URL, json={"name": "Sem loja", "sector_id": sector.id}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "STORE_ID_REQUIRED"


def test_master_creates_employee_for_any_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store(name="Loja Escolhida")
    sector = make_sector(store_id=store.id)
    make_user(email="master-emp2@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-emp2@kijapa.com", PASSWORD)

    response = client.post(
        EMPLOYEES_URL, json={"name": "Funcionário", "store_id": store.id, "sector_id": sector.id}, headers=headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["store_id"] == store.id


def test_operacional_cannot_create_employee(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="operacional-emp@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("operacional-emp@kijapa.com", PASSWORD)

    response = client.post(
        EMPLOYEES_URL, json={"name": "Sem permissão", "sector_id": sector.id}, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- listagem (a tela de seleção do tablet usa isso) ---------------------------


def test_operacional_can_list_employees_of_own_store(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    make_employee(store_id=store.id, name="Ativo 1")
    make_employee(store_id=store.id, name="Inativo", active=False)
    make_user(email="operacional-list@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("operacional-list@kijapa.com", PASSWORD)

    response = client.get(f"{EMPLOYEES_URL}?active_only=true", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    names = {employee["name"] for employee in response.json()}
    assert names == {"Ativo 1"}


def test_list_employees_only_shows_own_store(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_employee(store_id=store_a.id, name="Da Loja A")
    make_employee(store_id=store_b.id, name="Da Loja B")
    make_user(email="gestor-list@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-list@kijapa.com", PASSWORD)

    response = client.get(EMPLOYEES_URL, headers=headers)

    names = {employee["name"] for employee in response.json()}
    assert names == {"Da Loja A"}


# --- get / patch + isolamento entre lojas --------------------------------------


def test_gestor_cannot_view_employee_of_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    other_employee = make_employee(store_id=store_b.id, name="Da Loja B")
    make_user(email="gestor-get@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-get@kijapa.com", PASSWORD)

    response = client.get(f"{EMPLOYEES_URL}/{other_employee.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_unknown_employee_returns_404(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-404@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-404@kijapa.com", PASSWORD)

    response = client.get(f"{EMPLOYEES_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_gestor_deactivates_employee(client: TestClient, make_user, auth_headers, make_store, make_employee) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, name="Vai ser desativado")
    make_user(email="gestor-deact@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-deact@kijapa.com", PASSWORD)

    response = client.patch(f"{EMPLOYEES_URL}/{employee.id}", json={"active": False}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False


def test_gestor_cannot_edit_employee_of_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    other_employee = make_employee(store_id=store_b.id)
    make_user(email="gestor-edit@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-edit@kijapa.com", PASSWORD)

    response = client.patch(f"{EMPLOYEES_URL}/{other_employee.id}", json={"active": False}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- DELETE /employees/{id} --------------------------


def test_master_deletes_employee(client: TestClient, make_user, auth_headers, make_store, make_employee) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, name="Vai ser excluído")
    make_user(email="master-emp-delete1@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-emp-delete1@kijapa.com", PASSWORD)

    response = client.delete(f"{EMPLOYEES_URL}/{employee.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False

    entries = client.get("/api/v1/audit", headers=headers).json()
    actions = {
        entry["action"] for entry in entries if entry["entity_id"] == employee.id and entry["entity_type"] == "EMPLOYEE"
    }
    assert "DELETE" in actions


def test_deleted_employee_cannot_authenticate_pin(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="1234")
    make_user(email="master-emp-delete2@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-emp-delete2@kijapa.com", PASSWORD)

    client.delete(f"{EMPLOYEES_URL}/{employee.id}", headers=headers)

    response = client.post(f"{EMPLOYEES_URL}/{employee.id}/pin/authenticate", json={"pin": "1234"}, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_INACTIVE"


def test_gestor_cannot_delete_employee(client: TestClient, make_user, auth_headers, make_store, make_employee) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id)
    make_user(email="gestor-emp-delete@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-emp-delete@kijapa.com", PASSWORD)

    response = client.delete(f"{EMPLOYEES_URL}/{employee.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_lider_cannot_delete_employee(client: TestClient, make_user, auth_headers, make_store, make_employee) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id)
    make_user(email="lider-emp-delete@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("lider-emp-delete@kijapa.com", PASSWORD)

    response = client.delete(f"{EMPLOYEES_URL}/{employee.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_unknown_employee_returns_404(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master-emp-delete3@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-emp-delete3@kijapa.com", PASSWORD)

    response = client.delete(f"{EMPLOYEES_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_deleting_already_inactive_employee_is_idempotent(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, active=False)
    make_user(email="master-emp-delete4@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-emp-delete4@kijapa.com", PASSWORD)

    response = client.delete(f"{EMPLOYEES_URL}/{employee.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False
    entries = client.get("/api/v1/audit", headers=headers).json()
    delete_logs = [
        entry
        for entry in entries
        if entry["entity_id"] == employee.id and entry["entity_type"] == "EMPLOYEE" and entry["action"] == "DELETE"
    ]
    assert len(delete_logs) == 0
