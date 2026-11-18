
from fastapi import status
from fastapi.testclient import TestClient

from app.core.rate_limit import login_rate_limiter, pin_rate_limiter

AUTH_URL = "/api/v1/auth"
EMPLOYEES_URL = "/api/v1/employees"
PASSWORD = "SenhaForte123!"


def test_login_is_rate_limited_after_threshold(client: TestClient, make_user, make_store) -> None:
    store = make_store()
    make_user(email="rl-login@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)

    for _ in range(login_rate_limiter.max_requests):
        response = client.post(
            f"{AUTH_URL}/login", json={"email": "rl-login@kijapa.com", "password": "senha-errada"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # A tentativa seguinte já nem chega a checar a senha — 429 antes disso.
    limited_response = client.post(
        f"{AUTH_URL}/login", json={"email": "rl-login@kijapa.com", "password": "senha-errada"}
    )
    assert limited_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert limited_response.json()["code"] == "RATE_LIMITED"


def test_login_rate_limit_also_blocks_correct_password_once_exhausted(
    client: TestClient, make_user, make_store
) -> None:
    store = make_store()
    make_user(email="rl-login2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)

    for _ in range(login_rate_limiter.max_requests):
        client.post(f"{AUTH_URL}/login", json={"email": "rl-login2@kijapa.com", "password": "errada"})

    response = client.post(f"{AUTH_URL}/login", json={"email": "rl-login2@kijapa.com", "password": PASSWORD})

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_pin_authenticate_is_rate_limited_after_threshold(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    make_user(email="rl-pin@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("rl-pin@kijapa.com", PASSWORD)

    for _ in range(pin_rate_limiter.max_requests):
        employee = make_employee(store_id=store.id, pin="9999")
        response = client.post(
            f"{EMPLOYEES_URL}/{employee.id}/pin/authenticate", json={"pin": "0000"}, headers=headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    another_employee = make_employee(store_id=store.id, pin="9999")
    limited_response = client.post(
        f"{EMPLOYEES_URL}/{another_employee.id}/pin/authenticate", json={"pin": "0000"}, headers=headers
    )
    assert limited_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert limited_response.json()["code"] == "RATE_LIMITED"


def test_pin_rate_limit_is_shared_across_different_employees_from_same_ip(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store = make_store()
    employee_a = make_employee(store_id=store.id, pin="9999", name="Funcionário A")
    employee_b = make_employee(store_id=store.id, pin="9999", name="Funcionário B")
    make_user(email="rl-pin2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("rl-pin2@kijapa.com", PASSWORD)

    # Metade das tentativas contra um funcionário, metade contra outro — o
    # total ainda soma o limite máximo, vindo do mesmo IP.
    half = pin_rate_limiter.max_requests // 2
    for _ in range(half):
        client.post(f"{EMPLOYEES_URL}/{employee_a.id}/pin/authenticate", json={"pin": "0000"}, headers=headers)
    for _ in range(pin_rate_limiter.max_requests - half):
        client.post(f"{EMPLOYEES_URL}/{employee_b.id}/pin/authenticate", json={"pin": "0000"}, headers=headers)

    # A cota já esgotou — nem um PIN CORRETO de um terceiro funcionário passa.
    limited_response = client.post(
        f"{EMPLOYEES_URL}/{employee_a.id}/pin/authenticate", json={"pin": "9999"}, headers=headers
    )
    assert limited_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
