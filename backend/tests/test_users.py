
from datetime import datetime, timezone

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_secret
from app.models.refresh_token import RefreshToken
from app.models.user import User

USERS_URL = "/api/v1/users"
PASSWORD = "SenhaForte123!"


# --- criação --------------------------------------------------------------------


def test_master_creates_user_with_hashed_password(
    client: TestClient, make_user, auth_headers, make_store, db_session: Session
) -> None:
    store = make_store(name="Loja X")
    make_user(email="master1@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master1@kijapa.com", PASSWORD)

    response = client.post(
        USERS_URL,
        json={"name": "Novo Gestor", "email": "novo-gestor@kijapa.com", "password": "SenhaDoGestor1!", "role": "GESTOR", "store_id": store.id},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["email"] == "novo-gestor@kijapa.com"
    assert body["role"] == "GESTOR"
    assert body["store_id"] == store.id
    assert "password" not in body and "password_hash" not in body

    created = db_session.scalar(select(User).where(User.email == "novo-gestor@kijapa.com"))
    assert created is not None
    assert created.password_hash.startswith("$argon2id$")
    assert verify_secret("SenhaDoGestor1!", created.password_hash)


def test_new_user_is_created_with_must_change_password_and_audit_log(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="master-mcp1@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-mcp1@kijapa.com", PASSWORD)

    response = client.post(
        USERS_URL,
        json={
            "name": "Recém-Criado",
            "email": "recem-criado@kijapa.com",
            "password": "SenhaTemporaria1!",
            "role": "GESTOR",
            "store_id": store.id,
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["must_change_password"] is True

    audit_response = client.get("/api/v1/audit", headers=headers)
    entry = audit_response.json()[0]
    assert entry["action"] == "CREATE"
    assert entry["entity_type"] == "USER"
    assert entry["entity_id"] == body["id"]


def test_creating_master_user_ignores_client_store_id(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="master2@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master2@kijapa.com", PASSWORD)

    response = client.post(
        USERS_URL,
        json={"name": "Outro Master", "email": "outro-master@kijapa.com", "password": PASSWORD, "role": "MASTER", "store_id": store.id},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["store_id"] is None


def test_create_user_requires_store_id_for_non_master_role(
    client: TestClient, make_user, auth_headers
) -> None:
    make_user(email="master3@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master3@kijapa.com", PASSWORD)

    response = client.post(
        USERS_URL,
        json={"name": "Sem loja", "email": "sem-loja@kijapa.com", "password": PASSWORD, "role": "LIDER"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "STORE_ID_REQUIRED"


def test_create_user_with_unknown_store_returns_404(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master4@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master4@kijapa.com", PASSWORD)

    response = client.post(
        USERS_URL,
        json={"name": "X", "email": "x@kijapa.com", "password": PASSWORD, "role": "OPERACIONAL", "store_id": 999999},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_user_duplicate_email_returns_409(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="master5@kijapa.com", password=PASSWORD, role="MASTER")
    make_user(email="existente@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("master5@kijapa.com", PASSWORD)

    response = client.post(
        USERS_URL,
        json={"name": "Duplicado", "email": "existente@kijapa.com", "password": PASSWORD, "role": "GESTOR", "store_id": store.id},
        headers=headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "EMAIL_ALREADY_EXISTS"


def test_create_user_rejects_unknown_role(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master6@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master6@kijapa.com", PASSWORD)

    response = client.post(
        USERS_URL,
        json={"name": "X", "email": "papel-invalido@kijapa.com", "password": PASSWORD, "role": "SUPERVISOR"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_unauthenticated_cannot_create_user(client: TestClient) -> None:
    response = client.post(
        USERS_URL, json={"name": "X", "email": "x@kijapa.com", "password": PASSWORD, "role": "GESTOR", "store_id": 1}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_gestor_cannot_create_user(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-users@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-users@kijapa.com", PASSWORD)

    response = client.post(
        USERS_URL,
        json={"name": "X", "email": "x2@kijapa.com", "password": PASSWORD, "role": "OPERACIONAL", "store_id": store.id},
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_lider_cannot_manage_users(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="lider-users@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("lider-users@kijapa.com", PASSWORD)

    response = client.get(USERS_URL, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_operacional_cannot_manage_users(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="operacional-users@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("operacional-users@kijapa.com", PASSWORD)

    response = client.get(USERS_URL, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- listagem / detalhe -----------------------------------------------------------


def test_master_lists_and_filters_users(client: TestClient, make_user, auth_headers, make_store) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="master7@kijapa.com", password=PASSWORD, role="MASTER")
    make_user(email="gestor-a@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    make_user(email="gestor-b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    headers = auth_headers("master7@kijapa.com", PASSWORD)

    response = client.get(f"{USERS_URL}?store_id={store_a.id}", headers=headers)

    emails = {user["email"] for user in response.json()}
    assert emails == {"gestor-a@kijapa.com"}


def test_get_unknown_user_returns_404(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master8@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master8@kijapa.com", PASSWORD)

    response = client.get(f"{USERS_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


# --- edição ------------------------------------------------------------------------


def test_master_updates_user_role_and_store(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="master9@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(email="promovido@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store_a.id)
    headers = auth_headers("master9@kijapa.com", PASSWORD)

    response = client.patch(
        f"{USERS_URL}/{target.id}", json={"role": "GESTOR", "store_id": store_b.id}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["role"] == "GESTOR"
    assert body["store_id"] == store_b.id


def test_promoting_user_to_master_clears_store_id(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="master10@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(email="vira-master@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("master10@kijapa.com", PASSWORD)

    response = client.patch(f"{USERS_URL}/{target.id}", json={"role": "MASTER"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["store_id"] is None


def test_master_resets_user_password(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="master11@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(email="troca-senha@kijapa.com", password="SenhaAntiga123!", role="GESTOR", store_id=store.id)
    headers = auth_headers("master11@kijapa.com", PASSWORD)

    response = client.patch(f"{USERS_URL}/{target.id}", json={"password": "SenhaNova456!"}, headers=headers)
    assert response.status_code == status.HTTP_200_OK

    old_login = client.post("/api/v1/auth/login", json={"email": "troca-senha@kijapa.com", "password": "SenhaAntiga123!"})
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED

    new_login = client.post("/api/v1/auth/login", json={"email": "troca-senha@kijapa.com", "password": "SenhaNova456!"})
    assert new_login.status_code == status.HTTP_200_OK


def test_master_resetting_password_sets_must_change_password_and_logs_it(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="master11b@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(email="troca-senha2@kijapa.com", password="SenhaAntiga123!", role="GESTOR", store_id=store.id)
    headers = auth_headers("master11b@kijapa.com", PASSWORD)

    response = client.patch(f"{USERS_URL}/{target.id}", json={"password": "SenhaNova456!"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["must_change_password"] is True

    entry = client.get("/api/v1/audit", headers=headers).json()[0]
    assert entry["action"] == "RESET_PASSWORD"
    assert entry["entity_type"] == "USER"
    assert entry["entity_id"] == target.id


def test_resetting_password_together_with_other_fields_logs_two_audit_entries(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="master11c@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(email="troca-senha3@kijapa.com", password="SenhaAntiga123!", role="GESTOR", store_id=store.id)
    headers = auth_headers("master11c@kijapa.com", PASSWORD)

    response = client.patch(
        f"{USERS_URL}/{target.id}", json={"password": "SenhaNova456!", "active": False}, headers=headers
    )
    assert response.status_code == status.HTTP_200_OK

    entries = client.get("/api/v1/audit", headers=headers).json()
    actions = {entry["action"] for entry in entries if entry["entity_id"] == target.id and entry["entity_type"] == "USER"}
    assert actions == {"RESET_PASSWORD", "DEACTIVATE"}


def test_master_deactivates_user(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="master12@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(email="vai-desativar@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("master12@kijapa.com", PASSWORD)

    response = client.patch(f"{USERS_URL}/{target.id}", json={"active": False}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False


def test_non_master_cannot_update_user(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    gestor = make_user(email="gestor-upd@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-upd@kijapa.com", PASSWORD)

    response = client.patch(f"{USERS_URL}/{gestor.id}", json={"active": False}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- DELETE /users/{id} ----------------------------------


def test_master_deletes_user(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="master-delete1@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(email="vai-ser-excluido@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("master-delete1@kijapa.com", PASSWORD)

    response = client.delete(f"{USERS_URL}/{target.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False

    entries = client.get("/api/v1/audit", headers=headers).json()
    actions = {entry["action"] for entry in entries if entry["entity_id"] == target.id and entry["entity_type"] == "USER"}
    assert "DELETE" in actions


def test_deleted_user_cannot_login(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="master-delete2@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(email="sera-excluido@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("master-delete2@kijapa.com", PASSWORD)

    client.delete(f"{USERS_URL}/{target.id}", headers=headers)

    response = client.post("/api/v1/auth/login", json={"email": "sera-excluido@kijapa.com", "password": PASSWORD})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_master_cannot_delete_own_user(client: TestClient, make_user, auth_headers) -> None:
    master = make_user(email="master-self-delete@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-self-delete@kijapa.com", PASSWORD)

    response = client.delete(f"{USERS_URL}/{master.id}", headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "CANNOT_DELETE_SELF"


def test_gestor_cannot_delete_user(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="master-delete3@kijapa.com", password=PASSWORD, role="MASTER")
    gestor = make_user(email="gestor-delete@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    target = make_user(email="alvo-gestor@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("gestor-delete@kijapa.com", PASSWORD)

    response = client.delete(f"{USERS_URL}/{target.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_unknown_user_returns_404(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master-delete4@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-delete4@kijapa.com", PASSWORD)

    response = client.delete(f"{USERS_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_deleting_already_inactive_user_is_idempotent(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="master-delete5@kijapa.com", password=PASSWORD, role="MASTER")
    target = make_user(
        email="ja-inativo@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id, active=False
    )
    headers = auth_headers("master-delete5@kijapa.com", PASSWORD)

    response = client.delete(f"{USERS_URL}/{target.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False
    # Não deve duplicar log de DELETE pra quem já estava inativo.
    entries = client.get("/api/v1/audit", headers=headers).json()
    delete_logs = [
        entry
        for entry in entries
        if entry["entity_id"] == target.id and entry["entity_type"] == "USER" and entry["action"] == "DELETE"
    ]
    assert len(delete_logs) == 0


# --- expiração do refresh token por papel -----------------------------------------


def test_operational_refresh_token_has_long_expiry(
    client: TestClient, make_user, db_session: Session
) -> None:
    make_user(email="tablet@kijapa.com", password=PASSWORD, role="OPERACIONAL")

    client.post("/api/v1/auth/login", json={"email": "tablet@kijapa.com", "password": PASSWORD})

    token = db_session.scalar(
        select(RefreshToken).join(User).where(User.email == "tablet@kijapa.com")
    )
    assert token is not None
    days_valid = (token.expires_at - datetime.now(timezone.utc)).days
    assert days_valid > 300  # ~1 ano, bem acima do padrão de 7 dias


def test_gestor_refresh_token_has_default_short_expiry(
    client: TestClient, make_user, make_store, db_session: Session
) -> None:
    store = make_store()
    make_user(email="gestor-curto@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)

    client.post("/api/v1/auth/login", json={"email": "gestor-curto@kijapa.com", "password": PASSWORD})

    token = db_session.scalar(
        select(RefreshToken).join(User).where(User.email == "gestor-curto@kijapa.com")
    )
    assert token is not None
    days_valid = (token.expires_at - datetime.now(timezone.utc)).days
    assert days_valid <= 7
