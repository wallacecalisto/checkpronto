from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
}


def _code_for_status(status_code: int) -> str:
    return _CODE_BY_STATUS.get(status_code, "ERROR")


def _error_response(status_code: int, detail: str, code: str, **extra: object) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code, **extra})


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "message" in exc.detail:
        code = exc.detail.get("code") or _code_for_status(exc.status_code)
        extra = {key: value for key, value in exc.detail.items() if key not in ("message", "code")}
        return _error_response(exc.status_code, exc.detail["message"], code, **extra)
    return _error_response(exc.status_code, str(exc.detail), _code_for_status(exc.status_code))


def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Dados inválidos.",
        "VALIDATION_ERROR",
        errors=jsonable_encoder(exc.errors()),
    )


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Nunca vaza detalhe interno (mensagem de exceção, stack trace) para o cliente.
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erro interno do servidor.", "INTERNAL_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
