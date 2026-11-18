
from fastapi import status
from fastapi.testclient import TestClient

from app.services.pin_service import MAX_PIN_ATTEMPTS

EMPLOYEES_URL = "/api/v1/employees"
PASSWORD = "SenhaForte123!"


def _pin_url(employee_id: int, action: str) -> str:
    return f"{EMPLOYEES_URL}/{employee_id}/pin/{action}"


# --- primeiro acesso: setup ----------------------------------------------------


def test_authenticate_without_pin_requires_setup(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id)  # nasce sem PIN, como o gestor cadastraria
    make_user(email="op-setup1@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-setup1@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "1234"}, headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "PIN_NOT_SET"


def test_setup_pin_on_first_access_then_authenticate_works(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id)
    make_user(email="op-setup2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-setup2@kijapa.com", PASSWORD)

    setup_response = client.post(_pin_url(employee.id, "setup"), json={"pin": "4321"}, headers=headers)
    assert setup_response.status_code == status.HTTP_200_OK
    assert setup_response.json()["employee_id"] == employee.id

    # Acesso seguinte: agora autentica normalmente com o PIN criado.
    auth_response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "4321"}, headers=headers)
    assert auth_response.status_code == status.HTTP_200_OK
    assert auth_response.json()["employee_id"] == employee.id


def test_setup_pin_rejects_wrong_format(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id)
    make_user(email="op-setup3@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-setup3@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "setup"), json={"pin": "12"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_cannot_setup_pin_twice_without_reset(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="1111")  # já tem PIN
    make_user(email="op-setup4@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-setup4@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "setup"), json={"pin": "2222"}, headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "PIN_ALREADY_SET"


# --- uso do dia a dia -----------------------------------------------------------


def test_authenticate_with_correct_pin_succeeds(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="op-auth1@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-auth1@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "9999"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK


def test_authenticate_with_wrong_pin_fails(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="op-auth2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-auth2@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "0000"}, headers=headers)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "PIN_INCORRECT"


def test_inactive_employee_cannot_authenticate(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999", active=False)
    make_user(email="op-auth3@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-auth3@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "9999"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "EMPLOYEE_INACTIVE"


def test_operacional_from_another_store_cannot_authenticate_employee(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    employee_b = make_employee(store_id=store_b.id, pin="9999")
    make_user(email="op-auth4@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store_a.id)
    headers = auth_headers("op-auth4@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee_b.id, "authenticate"), json={"pin": "9999"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- bloqueio por tentativas erradas ---------------------------------------------


def test_pin_locks_after_max_wrong_attempts(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="op-lock1@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-lock1@kijapa.com", PASSWORD)

    for _ in range(MAX_PIN_ATTEMPTS):
        response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "0000"}, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # A tentativa seguinte já está bloqueada — nem chega a comparar o PIN.
    locked_response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "0000"}, headers=headers)
    assert locked_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    body = locked_response.json()
    assert body["code"] == "PIN_LOCKED"
    # O horário vem separado da mensagem — o frontend formata isso sozinho
    # (Intl.DateTimeFormat) em vez de recortar uma data de dentro de uma frase.
    assert "locked_until" in body and isinstance(body["locked_until"], str)


def test_correct_pin_still_rejected_while_locked(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="op-lock2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-lock2@kijapa.com", PASSWORD)

    for _ in range(MAX_PIN_ATTEMPTS):
        client.post(_pin_url(employee.id, "authenticate"), json={"pin": "0000"}, headers=headers)

    # Mesmo digitando o PIN CORRETO agora, continua bloqueado até o tempo passar.
    response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "9999"}, headers=headers)

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json()["code"] == "PIN_LOCKED"


# --- reset (MASTER/GESTOR/LIDER) ---------------------------------------------------


def test_gestor_can_reset_pin_and_employee_must_setup_again(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="gestor-reset1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-reset1@kijapa.com", PASSWORD)

    reset_response = client.post(_pin_url(employee.id, "reset"), headers=headers)
    assert reset_response.status_code == status.HTTP_200_OK
    assert reset_response.json()["has_pin"] is False

    # Igual ao primeiro acesso: autenticar agora exige criar um PIN novo.
    auth_response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "9999"}, headers=headers)
    assert auth_response.status_code == status.HTTP_409_CONFLICT
    assert auth_response.json()["code"] == "PIN_NOT_SET"

    # E o PIN antigo não é mais aceito nem via setup (é um PIN novo, diferente).
    setup_response = client.post(_pin_url(employee.id, "setup"), json={"pin": "1234"}, headers=headers)
    assert setup_response.status_code == status.HTTP_200_OK


def test_reset_also_clears_lockout(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="gestor-reset2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-reset2@kijapa.com", PASSWORD)

    for _ in range(MAX_PIN_ATTEMPTS):
        client.post(_pin_url(employee.id, "authenticate"), json={"pin": "0000"}, headers=headers)

    client.post(_pin_url(employee.id, "reset"), headers=headers)

    # PIN novo, sem nenhum bloqueio herdado do PIN anterior.
    client.post(_pin_url(employee.id, "setup"), json={"pin": "5555"}, headers=headers)
    response = client.post(_pin_url(employee.id, "authenticate"), json={"pin": "5555"}, headers=headers)
    assert response.status_code == status.HTTP_200_OK


def test_lider_can_reset_pin(client: TestClient, make_user, auth_headers, make_store, make_employee) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="lider-reset@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("lider-reset@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "reset"), headers=headers)

    assert response.status_code == status.HTTP_200_OK


def test_operacional_cannot_reset_pin(client: TestClient, make_user, auth_headers, make_store, make_employee) -> None:
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="op-reset@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-reset@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "reset"), headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_master_can_reset_pin(client: TestClient, make_user, auth_headers, make_store, make_employee) -> None:
    # Decisão revisada: MASTER também pode resetar PIN, junto com GESTOR/LIDER.
    store = make_store()
    employee = make_employee(store_id=store.id, pin="9999")
    make_user(email="master-reset@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-reset@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee.id, "reset"), headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["has_pin"] is False


def test_gestor_cannot_reset_pin_of_employee_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    employee_b = make_employee(store_id=store_b.id, pin="9999")
    make_user(email="gestor-reset3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-reset3@kijapa.com", PASSWORD)

    response = client.post(_pin_url(employee_b.id, "reset"), headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
