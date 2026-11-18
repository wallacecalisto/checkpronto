from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import StoreScope, get_current_store_scope, get_current_user, require_roles, resolve_scoped_store_id
from app.db.session import get_db
from app.models.sector import Sector
from app.models.user import User
from app.schemas.sector import SectorCreate, SectorPublic, SectorUpdate
from app.services import audit_service

router = APIRouter(prefix="/sectors", tags=["sectors"])

_MANAGE_ROLES = ("MASTER", "GESTOR", "LIDER")

_SECTOR_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado.")


def _get_sector_or_404(sector_id: int, db: Session) -> Sector:
    sector = db.get(Sector, sector_id)
    if sector is None:
        raise _SECTOR_NOT_FOUND
    return sector


def _audit_snapshot(sector: Sector) -> dict:
    return {"name": sector.name, "active": sector.active}


@router.post("", response_model=SectorPublic, status_code=status.HTTP_201_CREATED)
def create_sector(
    payload: SectorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> Sector:
    store_id = resolve_scoped_store_id(current_user, payload.store_id, db)

    sector = Sector(store_id=store_id, name=payload.name)
    db.add(sector)
    db.flush()  # precisa do sector.id para o audit log abaixo

    audit_service.log(
        db,
        store_id=store_id,
        action="CREATE",
        entity_type="SECTOR",
        entity_id=sector.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        after_data=_audit_snapshot(sector),
    )

    db.commit()
    db.refresh(sector)
    return sector


@router.get("", response_model=list[SectorPublic])
def list_sectors(
    active_only: bool = Query(default=False),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Sector]:
    # Qualquer papel autenticado pode listar — inclusive OPERACIONAL, que vai
    # precisar disso pra montar a tela de seleção de setor no tablet.
    query = select(Sector)
    if current_user.role == "MASTER":
        if store_id is not None:
            query = query.where(Sector.store_id == store_id)
    else:
        query = query.where(Sector.store_id == current_user.store_id)

    if active_only:
        query = query.where(Sector.active.is_(True))

    return list(db.scalars(query.order_by(Sector.name)))


@router.get("/{sector_id}", response_model=SectorPublic)
def get_sector(
    sector_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> Sector:
    sector = _get_sector_or_404(sector_id, db)
    scope.require(sector.store_id)
    return sector


@router.patch("/{sector_id}", response_model=SectorPublic)
def update_sector(
    sector_id: int,
    payload: SectorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> Sector:
    sector = _get_sector_or_404(sector_id, db)
    scope.require(sector.store_id)

    updates = payload.model_dump(exclude_unset=True)
    before_data = _audit_snapshot(sector)
    for field, value in updates.items():
        setattr(sector, field, value)

    db.add(sector)
    audit_service.log(
        db,
        store_id=sector.store_id,
        action=audit_service.action_for_update(updates),
        entity_type="SECTOR",
        entity_id=sector.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        before_data=before_data,
        after_data=_audit_snapshot(sector),
    )
    db.commit()
    db.refresh(sector)
    return sector


@router.delete("/{sector_id}", response_model=SectorPublic)
def delete_sector(
    sector_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER")),
    scope: StoreScope = Depends(get_current_store_scope),
) -> Sector:
    sector = _get_sector_or_404(sector_id, db)
    scope.require(sector.store_id)

    if sector.active:
        before_data = _audit_snapshot(sector)
        sector.active = False
        db.add(sector)
        audit_service.log(
            db,
            store_id=sector.store_id,
            action="DELETE",
            entity_type="SECTOR",
            entity_id=sector.id,
            actor_user_id=current_user.id,
            actor_name=current_user.name,
            before_data=before_data,
            after_data=_audit_snapshot(sector),
        )
        db.commit()
        db.refresh(sector)

    return sector
