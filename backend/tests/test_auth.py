from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.deps import get_current_user, require_roles


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"


# --- POST /auth/login ---------------------------------------------------------


def test_login_success_returns_access_token_and_sets_refresh_cookie(client: TestClient, make_user) -> None:
    make_user(email="gestor@kijapa.com", password="SenhaForte123!", role="GESTOR")

    response = client.post(LOGIN_URL, json={"email": "gestor@kijapa.com", "password": "SenhaForte123!"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "gestor@kijapa.com"
    assert body["access_token"]
    assert response.cookies.get("refresh_token") is not None


def test_login_wrong_password_is_rejected(client: TestClient, make_user) -> None:
    make_user(email="gestor2@kijapa.com", password="SenhaForte123!")

    response = client.post(LOGIN_URL, json={"email": "gestor2@kijapa.com", "password": "senha-errada"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "UNAUTHORIZED"


def test_login_unknown_email_is_rejected(client: TestClient) -> None:
    response = client.post(LOGIN_URL, json={"email": "ninguem@kijapa.com", "password": "qualquer-coisa"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_inactive_user_is_rejected(client: TestClient, make_user) -> None:
    make_user(email="inativo@kijapa.com", password="SenhaForte123!", active=False)

    response = client.post(LOGIN_URL, json={"email": "inativo@kijapa.com", "password": "SenhaForte123!"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- POST /auth/refresh --------------------------------------------------------


def test_refresh_rotates_token_and_old_cookie_stops_working(client: TestClient, make_user) -> None:
    make_user(email="refresh@kijapa.com", password="SenhaForte123!")
    client.post(LOGIN_URL, json={"email": "refresh@kijapa.com", "password": "SenhaForte123!"})
    old_refresh_cookie = client.cookies.get("refresh_token")

    refresh_response = client.post(REFRESH_URL)

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    new_refresh_cookie = client.cookies.get("refresh_token")
    assert new_refresh_cookie != old_refresh_cookie

    # Reusar o refresh token antigo (já rotacionado) precisa ser rejeitado.
    client.cookies.set("refresh_token", old_refresh_cookie)
    reuse_response = client.post(REFRESH_URL)
    assert reuse_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_without_cookie_is_rejected(client: TestClient) -> None:
    response = client.post(REFRESH_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_refresh_with_garbage_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set("refresh_token", "isso-nunca-foi-emitido-pelo-backend")

    response = client.post(REFRESH_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- POST /auth/logout ----------------------------------------------------------


def test_logout_revokes_refresh_token(client: TestClient, make_user) -> None:
    make_user(email="logout@kijapa.com", password="SenhaForte123!")
    client.post(LOGIN_URL, json={"email": "logout@kijapa.com", "password": "SenhaForte123!"})

    logout_response = client.post(LOGOUT_URL)
    assert logout_response.status_code == status.HTTP_204_NO_CONTENT

    refresh_response = client.post(REFRESH_URL)
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_rejects_missing_token(db_session: Session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=None, db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_rejects_expired_token(db_session: Session, make_user) -> None:
    user = make_user(email="expirado@kijapa.com", password="SenhaForte123!")
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(user.id),
        "role": user.role,
        "store_id": user.store_id,
        "type": "access",
        "iat": now - timedelta(minutes=60),
        "exp": now - timedelta(minutes=30),
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=security.ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=_bearer(expired_token), db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_rejects_inactive_user(db_session: Session, make_user) -> None:
    user = make_user(email="ficou-inativo@kijapa.com", password="SenhaForte123!", active=False)
    token = security.create_access_token(user_id=user.id, role=user.role, store_id=user.store_id)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=_bearer(token), db=db_session)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_returns_user_for_valid_token(db_session: Session, make_user) -> None:
    user = make_user(email="valido@kijapa.com", password="SenhaForte123!")
    token = security.create_access_token(user_id=user.id, role=user.role, store_id=user.store_id)

    result = get_current_user(credentials=_bearer(token), db=db_session)

    assert result.id == user.id


def test_require_roles_allows_matching_role(make_user) -> None:
    user = make_user(email="master@kijapa.com", password="SenhaForte123!", role="MASTER")
    dependency = require_roles("MASTER", "GESTOR")

    assert dependency(current_user=user) is user


def test_require_roles_rejects_other_role(make_user) -> None:
    user = make_user(email="operacional@kijapa.com", password="SenhaForte123!", role="OPERACIONAL")
    dependency = require_roles("MASTER")

    with pytest.raises(HTTPException) as exc_info:
        dependency(current_user=user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


CHANGE_PASSWORD_URL = "/api/v1/auth/change-password"


def test_user_with_must_change_password_is_blocked_from_ordinary_endpoint(
    client: TestClient, make_user, auth_headers
) -> None:
    make_user(
        email="senha-temp1@kijapa.com", password="SenhaTemporaria1!", role="GESTOR", must_change_password=True
    )
    headers = auth_headers("senha-temp1@kijapa.com", "SenhaTemporaria1!")

    response = client.get("/api/v1/tasks", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_user_with_must_change_password_can_still_call_change_password(
    client: TestClient, make_user, auth_headers
) -> None:
    make_user(
        email="senha-temp2@kijapa.com", password="SenhaTemporaria1!", role="GESTOR", must_change_password=True
    )
    headers = auth_headers("senha-temp2@kijapa.com", "SenhaTemporaria1!")

    response = client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": "SenhaTemporaria1!", "new_password": "SenhaDefinitiva1!"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["must_change_password"] is False


def test_change_password_with_wrong_current_password_is_rejected(
    client: TestClient, make_user, auth_headers
) -> None:
    make_user(email="senha-temp3@kijapa.com", password="SenhaTemporaria1!", role="GESTOR")
    headers = auth_headers("senha-temp3@kijapa.com", "SenhaTemporaria1!")

    response = client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": "senha-errada", "new_password": "SenhaDefinitiva1!"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "INVALID_CURRENT_PASSWORD"


def test_change_password_success_clears_flag_and_unlocks_ordinary_endpoint(
    client: TestClient, make_user, auth_headers
) -> None:
    make_user(
        email="senha-temp4@kijapa.com", password="SenhaTemporaria1!", role="GESTOR", must_change_password=True
    )
    headers = auth_headers("senha-temp4@kijapa.com", "SenhaTemporaria1!")

    change_response = client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": "SenhaTemporaria1!", "new_password": "SenhaDefinitiva1!"},
        headers=headers,
    )
    assert change_response.status_code == status.HTTP_200_OK

    # A mesma sessão (mesmo access_token) já deixa de ser bloqueada — o campo
    # virou False no banco, e get_current_user relê o usuário a cada chamada.
    response = client.get("/api/v1/tasks", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    # E o login seguinte já usa a senha nova.
    new_login = client.post(
        "/api/v1/auth/login", json={"email": "senha-temp4@kijapa.com", "password": "SenhaDefinitiva1!"}
    )
    assert new_login.status_code == status.HTTP_200_OK
