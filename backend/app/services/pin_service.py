
from datetime import datetime, timedelta, timezone

from app.core.security import hash_secret, verify_secret
from app.models.employee import Employee

MAX_PIN_ATTEMPTS = 5
PIN_LOCKOUT_MINUTES = 15


class PinAlreadySetError(Exception):
    """Tentativa de criar um PIN para um funcionário que já tem um."""


class PinNotSetError(Exception):
    """Tentativa de autenticar um funcionário que ainda não tem PIN — precisa criar um primeiro."""


class PinLockedError(Exception):
    """Bloqueado por tentativas erradas demais."""

    def __init__(self, locked_until: datetime) -> None:
        self.locked_until = locked_until
        super().__init__(f"PIN bloqueado até {locked_until.isoformat()}.")


class PinIncorrectError(Exception):
    """PIN informado não confere com o cadastrado."""


def setup_pin(employee: Employee, pin: str) -> None:
    if employee.pin_hash is not None:
        raise PinAlreadySetError()

    employee.pin_hash = hash_secret(pin)
    employee.pin_attempts = 0
    employee.pin_locked_until = None


def reset_pin(employee: Employee) -> None:
    """Apaga o PIN atual — no próximo acesso, o funcionário precisa criar um novo."""
    employee.pin_hash = None
    employee.pin_attempts = 0
    employee.pin_locked_until = None


def authenticate_with_pin(employee: Employee, pin: str) -> None:
    if employee.pin_hash is None:
        raise PinNotSetError()

    now = datetime.now(timezone.utc)
    if employee.pin_locked_until is not None and employee.pin_locked_until > now:
        raise PinLockedError(employee.pin_locked_until)

    if not verify_secret(pin, employee.pin_hash):
        employee.pin_attempts += 1
        if employee.pin_attempts >= MAX_PIN_ATTEMPTS:
            employee.pin_locked_until = now + timedelta(minutes=PIN_LOCKOUT_MINUTES)
        raise PinIncorrectError()

    # Acerto: zera o contador. Um PIN correto só é aceito se o bloqueio já tiver
    # passado (checado acima) — nunca "perdoa" o bloqueio antes da hora.
    employee.pin_attempts = 0
    employee.pin_locked_until = None
