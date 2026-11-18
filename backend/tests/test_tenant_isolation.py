
from fastapi import status
from fastapi.testclient import TestClient

STORES_URL = "/api/v1/stores"
PASSWORD = "SenhaForte123!"


def test_gestor_can_view_own_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    own_store = make_store(name="Loja do Gestor A")
    make_user(email="gestor-a@kijapa.com", password=PASSWORD, role="GESTOR", store_id=own_store.id)
    headers = auth_headers("gestor-a@kijapa.com", PASSWORD)

    response = client.get(f"{STORES_URL}/{own_store.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == own_store.id


def test_gestor_cannot_view_another_stores_data(client: TestClient, make_user, auth_headers, make_store) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="gestor-a2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-a2@kijapa.com", PASSWORD)

    # Gestor da Loja A tentando acessar a Loja B pelo ID, direto.
    response = client.get(f"{STORES_URL}/{store_b.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_operacional_cannot_view_another_stores_data(client: TestClient, make_user, auth_headers, make_store) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="operacional-a@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store_a.id)
    headers = auth_headers("operacional-a@kijapa.com", PASSWORD)

    response = client.get(f"{STORES_URL}/{store_b.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_lider_cannot_view_another_stores_data_even_guessing_valid_id(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    store_c = make_store(name="Loja C")
    make_user(email="lider-a@kijapa.com", password=PASSWORD, role="LIDER", store_id=store_a.id)
    headers = auth_headers("lider-a@kijapa.com", PASSWORD)

    # Nenhum ID de loja alheia funciona, mesmo variando (garante que não é coincidência).
    for other_store in (store_b, store_c):
        response = client.get(f"{STORES_URL}/{other_store.id}", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_master_can_view_any_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="master-iso@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-iso@kijapa.com", PASSWORD)

    for store in (store_a, store_b):
        response = client.get(f"{STORES_URL}/{store.id}", headers=headers)
        assert response.status_code == status.HTTP_200_OK


def test_user_without_store_cannot_view_any_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    # Caso de borda: um usuário não-MASTER sem store_id (inconsistência de dados)
    # não deve, por acidente, ganhar acesso a nada.
    store = make_store(name="Loja Qualquer")
    make_user(email="sem-loja@kijapa.com", password=PASSWORD, role="GESTOR", store_id=None)
    headers = auth_headers("sem-loja@kijapa.com", PASSWORD)

    response = client.get(f"{STORES_URL}/{store.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
