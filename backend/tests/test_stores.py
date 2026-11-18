from fastapi import status
from fastapi.testclient import TestClient

STORES_URL = "/api/v1/stores"
PASSWORD = "SenhaForte123!"


def test_master_can_create_store_dynamically(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master1@kijapa.com", password=PASSWORD, role="MASTER", store_id=None)
    headers = auth_headers("master1@kijapa.com", PASSWORD)

    # O nome não existe em lugar nenhum do código — vem só do corpo da requisição.
    payload = {"name": "Cozinha Vila Mariana", "brand": "Kijapa"}
    response = client.post(STORES_URL, json=payload, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["name"] == payload["name"]
    assert body["brand"] == payload["brand"]
    assert body["active"] is True
    assert isinstance(body["id"], int)


def test_create_store_without_authentication_is_rejected(client: TestClient) -> None:
    response = client.post(STORES_URL, json={"name": "Qualquer Loja"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_non_master_cannot_create_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store(name="Loja do Gestor")
    make_user(email="gestor1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor1@kijapa.com", PASSWORD)

    response = client.post(STORES_URL, json={"name": "Loja Nova"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_non_master_cannot_list_stores(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="lider1@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("lider1@kijapa.com", PASSWORD)

    response = client.get(STORES_URL, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_master_can_list_stores(client: TestClient, make_user, auth_headers, make_store) -> None:
    make_store(name="Loja 1")
    make_store(name="Loja 2")
    make_user(email="master2@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master2@kijapa.com", PASSWORD)

    response = client.get(STORES_URL, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    names = {store["name"] for store in response.json()}
    assert {"Loja 1", "Loja 2"}.issubset(names)


def test_master_can_update_and_deactivate_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store(name="Loja Antiga")
    make_user(email="master3@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master3@kijapa.com", PASSWORD)

    response = client.patch(
        f"{STORES_URL}/{store.id}", json={"name": "Loja Renomeada", "active": False}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == "Loja Renomeada"
    assert body["active"] is False


def test_non_master_cannot_update_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor2@kijapa.com", PASSWORD)

    response = client.patch(f"{STORES_URL}/{store.id}", json={"name": "Tentativa"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_unknown_store_returns_404(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master4@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master4@kijapa.com", PASSWORD)

    response = client.patch(f"{STORES_URL}/999999", json={"name": "Não existe"}, headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


# --- GET /stores/{id} escopado por loja -------


def test_gestor_can_view_own_store_name(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store(name="Loja da Gestora")
    make_user(email="gestor3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor3@kijapa.com", PASSWORD)

    response = client.get(f"{STORES_URL}/{store.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Loja da Gestora"
