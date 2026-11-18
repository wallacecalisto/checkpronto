from pydantic import BaseModel, Field

# Validado aqui (formato) e de novo no service (regra de negócio) — o Pydantic
# garante "são 4 dígitos", o service garante "está certo e não está bloqueado".
_PIN_PATTERN = r"^\d{4}$"


class PinSetupRequest(BaseModel):
    pin: str = Field(pattern=_PIN_PATTERN, description="4 dígitos numéricos.")


class PinAuthenticateRequest(BaseModel):
    pin: str = Field(pattern=_PIN_PATTERN)


class PinAuthenticateResponse(BaseModel):
    employee_id: int
    name: str
