from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import StoreScope, get_current_store_scope, require_roles
from app.db.session import get_db
from app.models.store import Store
from app.schemas.store import StoreCreate, StorePublic, StoreUpdate

router = APIRouter(prefix="/stores", tags=["stores"])

_STORE_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loja não encontrada.")


def _get_store_or_404(store_id: int, db: Session) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise _STORE_NOT_FOUND
    return store


@router.post("", response_model=StorePublic, status_code=status.HTTP_201_CREATED)
def create_store(
    payload: StoreCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("MASTER")),
) -> Store:
    store = Store(name=payload.name, brand=payload.brand)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("", response_model=list[StorePublic])
def list_stores(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("MASTER")),
) -> list[Store]:
    return list(db.scalars(select(Store).order_by(Store.id)))


@router.patch("/{store_id}", response_model=StorePublic)
def update_store(
    store_id: int,
    payload: StoreUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("MASTER")),
) -> Store:
    store = _get_store_or_404(store_id, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(store, field, value)

    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/{store_id}", response_model=StorePublic)
def get_store(
    store_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> Store:
    scope.require(store_id)
    return _get_store_or_404(store_id, db)
