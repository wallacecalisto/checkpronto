import json

from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.core.errors import unhandled_exception_handler, validation_exception_handler


def _body(response) -> dict:
    return json.loads(response.body)


def test_unknown_route_returns_standardized_404(client: TestClient) -> None:
    response = client.get("/rota-que-nao-existe")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert "detail" in body


def test_method_not_allowed_returns_standardized_405(client: TestClient) -> None:
    # /health só aceita GET.
    response = client.post("/health")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    body = response.json()
    assert body["code"] == "METHOD_NOT_ALLOWED"
    assert "detail" in body


def test_validation_error_handler_format() -> None:
    exc = RequestValidationError(
        errors=[{"loc": ("query", "x"), "msg": "campo obrigatório", "type": "missing"}]
    )

    response = validation_exception_handler(request=None, exc=exc)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    body = _body(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"][0]["loc"] == ["query", "x"]


def test_unhandled_exception_handler_format() -> None:
    response = unhandled_exception_handler(request=None, exc=RuntimeError("detalhe interno sensível"))

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    body = _body(response)
    assert body["code"] == "INTERNAL_ERROR"
    # A mensagem da exceção original nunca deve vazar para o cliente.
    assert "detalhe interno sensível" not in body["detail"]


def test_responses_include_security_headers(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_cors_preflight_allows_configured_origin_with_explicit_methods(client: TestClient) -> None:
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    allowed_methods = {method.strip() for method in response.headers["access-control-allow-methods"].split(",")}
    assert allowed_methods == {"GET", "POST", "PATCH", "DELETE", "OPTIONS"}


def test_cors_preflight_rejects_unconfigured_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://site-malicioso.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers
