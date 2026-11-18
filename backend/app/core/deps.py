from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.employee import Employee
from app.models.store import Store
from app.models.user import User
from app.services import pin_service

_bearer_scheme = HTTPBearer(auto_error=False, description="Cole aqui o access_token retornado por POST /auth/login.")

_NOT_AUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não autenticado.",
    headers={"WWW-Authenticate": "Bearer"},
)

_PASSWORD_CHANGE_REQUIRED = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={
        "message": "Você precisa definir uma nova senha antes de continuar.",
        "code": "PASSWORD_CHANGE_REQUIRED",
    },
)


def _resolve_current_user(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
) -> User:
    if credentials is None:
        raise _NOT_AUTHENTICATED

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise _NOT_AUTHENTICATED from exc

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.active:
        raise _NOT_AUTHENTICATED

    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user = _resolve_current_user(credentials, db)
    if user.must_change_password:
        raise _PASSWORD_CHANGE_REQUIRED
    return user


def get_current_user_allow_password_change(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    return _resolve_current_user(credentials, db)


def require_roles(*allowed_roles: str):

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso.",
            )
        return current_user

    return dependency


@dataclass
class StoreScope:

    user: User
    is_master: bool

    def allows(self, store_id: int) -> bool:
        if self.is_master:
            return True
        return self.user.store_id == store_id

    def require(self, store_id: int) -> None:
        if not self.allows(store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar dados desta loja.",
            )


def get_current_store_scope(
    current_user: Annotated[User, Depends(get_current_user)],
) -> StoreScope:
    return StoreScope(user=current_user, is_master=current_user.role == "MASTER")


def resolve_scoped_store_id(current_user: User, payload_store_id: int | None, db: Session) -> int:
    if current_user.role != "MASTER":
        return current_user.store_id

    if payload_store_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "store_id é obrigatório para o papel MASTER.", "code": "STORE_ID_REQUIRED"},
        )
    if db.get(Store, payload_store_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loja não encontrada.")
    return payload_store_id


def require_pin_verified_employee(
    employee_id: int | None, pin: str | None, db: Session, scope: "StoreScope"
) -> Employee:
    if employee_id is None or pin is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "employee_id e pin são obrigatórios para esta ação.", "code": "PIN_REQUIRED"},
        )

    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado.")
    scope.require(employee.store_id)

    if not employee.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Funcionário inativo.", "code": "EMPLOYEE_INACTIVE"},
        )

    try:
        pin_service.authenticate_with_pin(employee, pin)
    except pin_service.PinNotSetError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Este funcionário ainda não tem um PIN cadastrado.", "code": "PIN_NOT_SET"},
        ) from None
    except pin_service.PinLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": f"PIN bloqueado. Tente novamente após {exc.locked_until.isoformat()}.",
                "code": "PIN_LOCKED",
                "locked_until": exc.locked_until.isoformat(),
            },
        ) from None
    except pin_service.PinIncorrectError:
        db.add(employee)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "PIN incorreto.", "code": "PIN_INCORRECT"},
        ) from None

    db.add(employee)
    db.commit()
    return employee
