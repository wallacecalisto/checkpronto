
from fastapi import status
from fastapi.testclient import TestClient

SECTORS_URL = "/api/v1/sectors"
PASSWORD = "SenhaForte123!"


# --- criação -----------------------------------------------------------------


def test_gestor_creates_sector_in_own_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store(name="Loja do Gestor")
    make_user(email="gestor-sec1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-sec1@kijapa.com", PASSWORD)

    response = client.post(SECTORS_URL, json={"name": "Cozinha Quente"}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["name"] == "Cozinha Quente"
    assert body["store_id"] == store.id
    assert body["active"] is True


def test_lider_creates_sector_in_own_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="lider-sec1@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("lider-sec1@kijapa.com", PASSWORD)

    response = client.post(SECTORS_URL, json={"name": "Sushi"}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED


def test_gestor_cannot_create_sector_in_another_store_by_faking_store_id(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    own_store = make_store(name="Loja A")
    other_store = make_store(name="Loja B")
    make_user(email="gestor-sec2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=own_store.id)
    headers = auth_headers("gestor-sec2@kijapa.com", PASSWORD)

    response = client.post(SECTORS_URL, json={"name": "Tentativa", "store_id": other_store.id}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["store_id"] == own_store.id


def test_master_must_specify_store_id_to_create_sector(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master-sec1@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-sec1@kijapa.com", PASSWORD)

    response = client.post(SECTORS_URL, json={"name": "Sem loja"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "STORE_ID_REQUIRED"


def test_master_creates_sector_for_any_store(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store(name="Loja Escolhida")
    make_user(email="master-sec2@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-sec2@kijapa.com", PASSWORD)

    response = client.post(SECTORS_URL, json={"name": "Atendimento", "store_id": store.id}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["store_id"] == store.id


def test_operacional_cannot_create_sector(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="operacional-sec1@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("operacional-sec1@kijapa.com", PASSWORD)

    response = client.post(SECTORS_URL, json={"name": "Sem permissão"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_sector_without_authentication_is_rejected(client: TestClient) -> None:
    response = client.post(SECTORS_URL, json={"name": "Qualquer Setor"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- listagem ---------


def test_operacional_can_list_sectors_of_own_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    make_sector(store_id=store.id, name="Cozinha Fria")
    make_user(email="operacional-sec2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("operacional-sec2@kijapa.com", PASSWORD)

    response = client.get(SECTORS_URL, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    names = {sector["name"] for sector in response.json()}
    assert "Cozinha Fria" in names


def test_list_sectors_only_shows_own_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    own_store = make_store(name="Loja Própria")
    other_store = make_store(name="Loja Alheia")
    make_sector(store_id=own_store.id, name="Setor Próprio")
    make_sector(store_id=other_store.id, name="Setor Alheio")
    make_user(email="gestor-sec3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=own_store.id)
    headers = auth_headers("gestor-sec3@kijapa.com", PASSWORD)

    response = client.get(SECTORS_URL, headers=headers)

    names = {sector["name"] for sector in response.json()}
    assert "Setor Próprio" in names
    assert "Setor Alheio" not in names


def test_master_can_filter_sectors_by_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_sector(store_id=store_a.id, name="Setor A")
    make_sector(store_id=store_b.id, name="Setor B")
    make_user(email="master-sec3@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-sec3@kijapa.com", PASSWORD)

    response = client.get(f"{SECTORS_URL}?store_id={store_a.id}", headers=headers)

    names = {sector["name"] for sector in response.json()}
    assert names == {"Setor A"}


def test_active_only_filter_hides_inactive_sectors(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    make_sector(store_id=store.id, name="Ativo")
    make_sector(store_id=store.id, name="Inativo", active=False)
    make_user(email="gestor-sec4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-sec4@kijapa.com", PASSWORD)

    response = client.get(f"{SECTORS_URL}?active_only=true", headers=headers)

    names = {sector["name"] for sector in response.json()}
    assert names == {"Ativo"}


# --- detalhe -------------------------------------------------------------------


def test_gestor_cannot_view_sector_of_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    own_store = make_store(name="Loja A")
    other_store = make_store(name="Loja B")
    other_sector = make_sector(store_id=other_store.id)
    make_user(email="gestor-sec5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=own_store.id)
    headers = auth_headers("gestor-sec5@kijapa.com", PASSWORD)

    response = client.get(f"{SECTORS_URL}/{other_sector.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_unknown_sector_returns_404(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master-sec4@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-sec4@kijapa.com", PASSWORD)

    response = client.get(f"{SECTORS_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


# --- edição --------------------------------------------------------------------


def test_gestor_updates_own_sector(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id, name="Nome Antigo")
    make_user(email="gestor-sec6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-sec6@kijapa.com", PASSWORD)

    response = client.patch(f"{SECTORS_URL}/{sector.id}", json={"name": "Nome Novo"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Nome Novo"


def test_gestor_deactivates_sector(client: TestClient, make_user, auth_headers, make_store, make_sector) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="gestor-sec7@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-sec7@kijapa.com", PASSWORD)

    response = client.patch(f"{SECTORS_URL}/{sector.id}", json={"active": False}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False


def test_gestor_cannot_edit_sector_of_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    own_store = make_store(name="Loja A")
    other_store = make_store(name="Loja B")
    other_sector = make_sector(store_id=other_store.id)
    make_user(email="gestor-sec8@kijapa.com", password=PASSWORD, role="GESTOR", store_id=own_store.id)
    headers = auth_headers("gestor-sec8@kijapa.com", PASSWORD)

    response = client.patch(f"{SECTORS_URL}/{other_sector.id}", json={"active": False}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_operacional_cannot_update_sector(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="operacional-sec3@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("operacional-sec3@kijapa.com", PASSWORD)

    response = client.patch(f"{SECTORS_URL}/{sector.id}", json={"name": "Indevido"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- exclusão -----------------------------------


def test_master_deletes_sector(client: TestClient, make_user, auth_headers, make_store, make_sector) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="master-sec5@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-sec5@kijapa.com", PASSWORD)

    response = client.delete(f"{SECTORS_URL}/{sector.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False


def test_gestor_cannot_delete_sector(client: TestClient, make_user, auth_headers, make_store, make_sector) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="gestor-sec9@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-sec9@kijapa.com", PASSWORD)

    response = client.delete(f"{SECTORS_URL}/{sector.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_lider_cannot_delete_sector(client: TestClient, make_user, auth_headers, make_store, make_sector) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id)
    make_user(email="lider-sec2@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("lider-sec2@kijapa.com", PASSWORD)

    response = client.delete(f"{SECTORS_URL}/{sector.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_master_cannot_delete_sector_of_wrong_store_id_guessed(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    # MASTER enxerga qualquer loja — este teste é só sobre 404 em id inexistente.
    make_user(email="master-sec6@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-sec6@kijapa.com", PASSWORD)

    response = client.delete(f"{SECTORS_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_deleting_already_inactive_sector_is_idempotent(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    sector = make_sector(store_id=store.id, active=False)
    make_user(email="master-sec7@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-sec7@kijapa.com", PASSWORD)

    response = client.delete(f"{SECTORS_URL}/{sector.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False
