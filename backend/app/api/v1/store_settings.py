from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import StoreScope, get_current_store_scope, require_roles
from app.db.session import get_db
from app.models.store import Store
from app.models.store_settings import StoreSettings
from app.schemas.store_settings import StoreSettingsPublic, StoreSettingsUpdate
from app.services import store_settings_service

router = APIRouter(prefix="/stores", tags=["store-settings"])

_STORE_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loja não encontrada.")


@router.get("/{store_id}/settings", response_model=StoreSettingsPublic)
def get_store_settings(
    store_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> StoreSettings:
    scope.require(store_id)
    if db.get(Store, store_id) is None:
        raise _STORE_NOT_FOUND
    return store_settings_service.get_effective_settings(db, store_id)


@router.patch("/{store_id}/settings", response_model=StoreSettingsPublic)
def update_store_settings(
    store_id: int,
    payload: StoreSettingsUpdate,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
    _current_user=Depends(require_roles("MASTER", "GESTOR")),
) -> StoreSettings:
    scope.require(store_id)
    if db.get(Store, store_id) is None:
        raise _STORE_NOT_FOUND

    updates = payload.model_dump(exclude_unset=True)
    return store_settings_service.upsert(db, store_id, updates)
