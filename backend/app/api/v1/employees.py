from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import StoreScope, get_current_store_scope, get_current_user, require_roles, resolve_scoped_store_id
from app.core.rate_limit import enforce_pin_rate_limit
from app.db.session import get_db
from app.models.employee import Employee
from app.models.sector import Sector
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeePublic, EmployeeUpdate
from app.schemas.pin import PinAuthenticateRequest, PinAuthenticateResponse, PinSetupRequest
from app.services import audit_service, pin_service

router = APIRouter(prefix="/employees", tags=["employees"])

# Quem pode cadastrar/editar funcionários e resetar PIN. O reset é ainda mais
# restrito (só GESTOR/LIDER, sem MASTER) — ver reset_employee_pin abaixo.
_MANAGE_ROLES = ("MASTER", "GESTOR", "LIDER")

_EMPLOYEE_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado.")
_SECTOR_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado.")


def _to_public(employee: Employee) -> EmployeePublic:
    return EmployeePublic(
        id=employee.id,
        store_id=employee.store_id,
        sector_id=employee.sector_id,
        name=employee.name,
        role_title=employee.role_title,
        active=employee.active,
        has_pin=employee.pin_hash is not None,
    )


def _get_employee_or_404(employee_id: int, db: Session) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise _EMPLOYEE_NOT_FOUND
    return employee


def _validate_sector_belongs_to_store(sector_id: int, store_id: int, db: Session) -> None:
    sector = db.get(Sector, sector_id)
    if sector is None or sector.store_id != store_id:
        raise _SECTOR_NOT_FOUND


def _audit_snapshot(employee: Employee) -> dict:
    # Nunca pin_hash/pin_attempts/pin_locked_until aqui — a auditoria é para
    # gestores lerem, não um lugar para dado sensível de autenticação.
    return {
        "name": employee.name,
        "role_title": employee.role_title,
        "sector_id": employee.sector_id,
        "active": employee.active,
    }


# --- CRUD -----------------------------------------------------------------------


@router.post("", response_model=EmployeePublic, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> EmployeePublic:
    store_id = resolve_scoped_store_id(current_user, payload.store_id, db)
    _validate_sector_belongs_to_store(payload.sector_id, store_id, db)

    employee = Employee(
        store_id=store_id, sector_id=payload.sector_id, name=payload.name, role_title=payload.role_title
    )
    db.add(employee)
    db.flush()  # precisa do employee.id para o audit log abaixo

    audit_service.log(
        db,
        store_id=store_id,
        action="CREATE",
        entity_type="EMPLOYEE",
        entity_id=employee.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        after_data=_audit_snapshot(employee),
    )

    db.commit()
    db.refresh(employee)
    return _to_public(employee)


@router.get("", response_model=list[EmployeePublic])
def list_employees(
    active_only: bool = Query(default=False),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmployeePublic]:
    # Qualquer papel autenticado pode listar — inclusive OPERACIONAL, que
    # precisa disso para montar a tela de seleção de funcionário no tablet.
    query = select(Employee)
    if current_user.role == "MASTER":
        if store_id is not None:
            query = query.where(Employee.store_id == store_id)
    else:
        query = query.where(Employee.store_id == current_user.store_id)

    if active_only:
        query = query.where(Employee.active.is_(True))

    employees = db.scalars(query.order_by(Employee.name)).all()
    return [_to_public(employee) for employee in employees]


@router.get("/{employee_id}", response_model=EmployeePublic)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> EmployeePublic:
    employee = _get_employee_or_404(employee_id, db)
    scope.require(employee.store_id)
    return _to_public(employee)


@router.patch("/{employee_id}", response_model=EmployeePublic)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> EmployeePublic:
    employee = _get_employee_or_404(employee_id, db)
    scope.require(employee.store_id)

    updates = payload.model_dump(exclude_unset=True)
    if "sector_id" in updates:
        _validate_sector_belongs_to_store(updates["sector_id"], employee.store_id, db)

    before_data = _audit_snapshot(employee)
    for field, value in updates.items():
        setattr(employee, field, value)

    db.add(employee)
    audit_service.log(
        db,
        store_id=employee.store_id,
        action=audit_service.action_for_update(updates),
        entity_type="EMPLOYEE",
        entity_id=employee.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        before_data=before_data,
        after_data=_audit_snapshot(employee),
    )
    db.commit()
    db.refresh(employee)
    return _to_public(employee)


@router.delete("/{employee_id}", response_model=EmployeePublic)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER")),
    scope: StoreScope = Depends(get_current_store_scope),
) -> EmployeePublic:
    employee = _get_employee_or_404(employee_id, db)
    scope.require(employee.store_id)

    if employee.active:
        before_data = _audit_snapshot(employee)
        employee.active = False
        db.add(employee)
        audit_service.log(
            db,
            store_id=employee.store_id,
            action="DELETE",
            entity_type="EMPLOYEE",
            entity_id=employee.id,
            actor_user_id=current_user.id,
            actor_name=current_user.name,
            before_data=before_data,
            after_data=_audit_snapshot(employee),
        )
        db.commit()
        db.refresh(employee)

    return _to_public(employee)


# --- PIN ---------------------------------------------------------------------


@router.post("/{employee_id}/pin/setup", response_model=PinAuthenticateResponse)
def setup_employee_pin(
    employee_id: int,
    payload: PinSetupRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> PinAuthenticateResponse:
    employee = _get_employee_or_404(employee_id, db)
    scope.require(employee.store_id)

    if not employee.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Funcionário inativo.", "code": "EMPLOYEE_INACTIVE"},
        )

    try:
        pin_service.setup_pin(employee, payload.pin)
    except pin_service.PinAlreadySetError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Este funcionário já tem um PIN definido. Peça a um gestor ou líder para resetar.",
                "code": "PIN_ALREADY_SET",
            },
        ) from None

    db.add(employee)
    db.commit()
    return PinAuthenticateResponse(employee_id=employee.id, name=employee.name)


@router.post(
    "/{employee_id}/pin/authenticate",
    response_model=PinAuthenticateResponse,
    dependencies=[Depends(enforce_pin_rate_limit)],
)
def authenticate_employee_pin(
    employee_id: int,
    payload: PinAuthenticateRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> PinAuthenticateResponse:
    employee = _get_employee_or_404(employee_id, db)
    scope.require(employee.store_id)

    if not employee.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Funcionário inativo.", "code": "EMPLOYEE_INACTIVE"},
        )

    try:
        pin_service.authenticate_with_pin(employee, payload.pin)
    except pin_service.PinNotSetError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Este funcionário ainda não tem um PIN cadastrado.", "code": "PIN_NOT_SET"},
        ) from None
    except pin_service.PinLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": f"PIN bloqueado por tentativas incorretas. Tente novamente após {exc.locked_until.isoformat()}.",
                "code": "PIN_LOCKED",
                # ISO separado da mensagem: o frontend formata isso com Intl.DateTimeFormat
                # (fuso do Brasil) em vez de tentar recortar uma data de dentro da frase.
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
    return PinAuthenticateResponse(employee_id=employee.id, name=employee.name)


@router.post("/{employee_id}/pin/reset", response_model=EmployeePublic)
def reset_employee_pin(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER", "GESTOR", "LIDER")),
    scope: StoreScope = Depends(get_current_store_scope),
) -> EmployeePublic:
    employee = _get_employee_or_404(employee_id, db)
    scope.require(employee.store_id)

    pin_service.reset_pin(employee)
    db.add(employee)

    audit_service.log(
        db,
        store_id=employee.store_id,
        action="RESET_PIN",
        entity_type="EMPLOYEE",
        entity_id=employee.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
    )

    db.commit()
    db.refresh(employee)
    return _to_public(employee)
