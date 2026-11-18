from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.core.security import hash_secret
from app.db.session import get_db
from app.models.store import Store
from app.models.user import User
from app.schemas.user import UserCreate, UserPublic, UserUpdate
from app.services import audit_service

# Estritamente MASTER — nenhum outro papel gerencia a tabela de usuários,
# nem mesmo LIDER/GESTOR sobre usuários da própria loja (regra explícita).
router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_roles("MASTER"))])

_USER_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
_EMAIL_CONFLICT = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={"message": "Já existe um usuário com este e-mail.", "code": "EMAIL_ALREADY_EXISTS"},
)
_CANNOT_DELETE_SELF = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    detail={"message": "Você não pode excluir seu próprio usuário.", "code": "CANNOT_DELETE_SELF"},
)


def _to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        store_id=user.store_id,
        active=user.active,
        must_change_password=user.must_change_password,
    )


def _audit_snapshot(user: User) -> dict:
    # Nunca password_hash aqui — mesma regra de employees.py::_audit_snapshot.
    return {
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "store_id": user.store_id,
        "active": user.active,
    }


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise _USER_NOT_FOUND
    return user


def _resolve_store_id(role: str, store_id: int | None, db: Session) -> int | None:
    if role == "MASTER":
        return None

    if store_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "store_id é obrigatório para este papel.", "code": "STORE_ID_REQUIRED"},
        )
    if db.get(Store, store_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loja não encontrada.")
    return store_id


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER")),
) -> UserPublic:
    store_id = _resolve_store_id(payload.role, payload.store_id, db)

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_secret(payload.password),
        role=payload.role,
        store_id=store_id,
        # Todo acesso novo nasce com senha temporária — a pessoa é obrigada a
        # trocá-la no primeiro login (ver app/core/deps.py::get_current_user).
        must_change_password=True,
    )
    db.add(user)
    try:
        db.flush()  # precisa do user.id para o audit log abaixo
    except IntegrityError:
        db.rollback()
        raise _EMAIL_CONFLICT from None

    audit_service.log(
        db,
        store_id=store_id,
        action="CREATE",
        entity_type="USER",
        entity_id=user.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        after_data=_audit_snapshot(user),
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _EMAIL_CONFLICT from None

    db.refresh(user)
    return _to_public(user)


@router.get("", response_model=list[UserPublic])
def list_users(
    role: str | None = Query(default=None),
    store_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[UserPublic]:
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    if store_id is not None:
        query = query.where(User.store_id == store_id)

    users = db.scalars(query.order_by(User.id)).all()
    return [_to_public(user) for user in users]


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserPublic:
    return _to_public(_get_user_or_404(user_id, db))


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER")),
) -> UserPublic:
    user = _get_user_or_404(user_id, db)

    updates = payload.model_dump(exclude_unset=True, exclude={"password"})
    before_data = _audit_snapshot(user)

    # Papel e/ou loja mudando: revalida a combinação com a mesma regra da criação.
    if "role" in updates or "store_id" in updates:
        new_role = updates.get("role", user.role)
        new_store_id = updates.get("store_id", user.store_id)
        updates["store_id"] = _resolve_store_id(new_role, new_store_id, db)

    for field, value in updates.items():
        setattr(user, field, value)

    if updates:
        audit_service.log(
            db,
            store_id=user.store_id,
            action=audit_service.action_for_update(updates),
            entity_type="USER",
            entity_id=user.id,
            actor_user_id=current_user.id,
            actor_name=current_user.name,
            before_data=before_data,
            after_data=_audit_snapshot(user),
        )

    if payload.password is not None:
        user.password_hash = hash_secret(payload.password)
        user.must_change_password = True
        audit_service.log(
            db,
            store_id=user.store_id,
            action="RESET_PASSWORD",
            entity_type="USER",
            entity_id=user.id,
            actor_user_id=current_user.id,
            actor_name=current_user.name,
        )

    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _EMAIL_CONFLICT from None

    db.refresh(user)
    return _to_public(user)


@router.delete("/{user_id}", response_model=UserPublic)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER")),
) -> UserPublic:
    user = _get_user_or_404(user_id, db)
    if user.id == current_user.id:
        raise _CANNOT_DELETE_SELF

    if user.active:
        before_data = _audit_snapshot(user)
        user.active = False
        db.add(user)
        audit_service.log(
            db,
            store_id=user.store_id,
            action="DELETE",
            entity_type="USER",
            entity_id=user.id,
            actor_user_id=current_user.id,
            actor_name=current_user.name,
            before_data=before_data,
            after_data=_audit_snapshot(user),
        )
        db.commit()
        db.refresh(user)

    return _to_public(user)
