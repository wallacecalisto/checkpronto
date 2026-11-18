from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import StoreScope, get_current_store_scope, get_current_user, require_roles, resolve_scoped_store_id
from app.db.session import get_db
from app.models.checklist import ChecklistTemplate, ChecklistTemplateItem
from app.models.sector import Sector
from app.models.user import User
from app.schemas.checklist_template import (
    ChecklistTemplateCreate,
    ChecklistTemplateItemCreate,
    ChecklistTemplateItemPublic,
    ChecklistTemplateItemUpdate,
    ChecklistTemplatePublic,
    ChecklistTemplateUpdate,
)
from app.services import audit_service

router = APIRouter(prefix="/checklist-templates", tags=["checklist-templates"])
items_router = APIRouter(prefix="/checklist-template-items", tags=["checklist-templates"])

_MANAGE_ROLES = ("MASTER", "GESTOR", "LIDER")

_TEMPLATE_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template não encontrado.")
_ITEM_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado.")
_SECTOR_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setor não encontrado.")


def _validate_sector_belongs_to_store(sector_id: int, store_id: int, db: Session) -> Sector:
    sector = db.get(Sector, sector_id)
    if sector is None or sector.store_id != store_id:
        raise _SECTOR_NOT_FOUND
    if not sector.active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Este setor está desativado.", "code": "SECTOR_INACTIVE"},
        )
    return sector


def _item_to_public(item: ChecklistTemplateItem) -> ChecklistTemplateItemPublic:
    return ChecklistTemplateItemPublic(
        id=item.id,
        template_id=item.template_id,
        description=item.description,
        order_index=item.order_index,
        required=item.required,
        requires_photo=item.requires_photo,
        active=item.active,
    )


def _template_to_public(template: ChecklistTemplate) -> ChecklistTemplatePublic:
    items = sorted(template.items, key=lambda item: item.order_index)
    return ChecklistTemplatePublic(
        id=template.id,
        store_id=template.store_id,
        name=template.name,
        active=template.active,
        created_by_user_id=template.created_by_user_id,
        target_sector_id=template.target_sector_id,
        shift=template.shift,
        created_at=template.created_at,
        items=[_item_to_public(item) for item in items],
    )


def _get_template_or_404(template_id: int, db: Session) -> ChecklistTemplate:
    template = db.get(ChecklistTemplate, template_id)
    if template is None:
        raise _TEMPLATE_NOT_FOUND
    return template


def _get_item_or_404(item_id: int, db: Session) -> ChecklistTemplateItem:
    item = db.get(ChecklistTemplateItem, item_id)
    if item is None:
        raise _ITEM_NOT_FOUND
    return item


def _template_audit_snapshot(template: ChecklistTemplate) -> dict:
    return {
        "name": template.name,
        "active": template.active,
        "target_sector_id": template.target_sector_id,
        "shift": template.shift,
    }


def _item_audit_snapshot(item: ChecklistTemplateItem) -> dict:
    return {
        "description": item.description,
        "order_index": item.order_index,
        "required": item.required,
        "requires_photo": item.requires_photo,
        "active": item.active,
    }


@router.post("", response_model=ChecklistTemplatePublic, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: ChecklistTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> ChecklistTemplatePublic:
    store_id = resolve_scoped_store_id(current_user, payload.store_id, db)
    if payload.target_sector_id is not None:
        _validate_sector_belongs_to_store(payload.target_sector_id, store_id, db)

    template = ChecklistTemplate(
        store_id=store_id,
        name=payload.name,
        created_by_user_id=current_user.id,
        target_sector_id=payload.target_sector_id,
        shift=payload.shift,
    )
    db.add(template)
    db.flush()  # precisa do template.id para gravar os itens e o audit log abaixo

    for item_payload in payload.items:
        db.add(
            ChecklistTemplateItem(
                template_id=template.id,
                description=item_payload.description,
                order_index=item_payload.order_index,
                required=item_payload.required,
                requires_photo=item_payload.requires_photo,
            )
        )

    audit_service.log(
        db,
        store_id=store_id,
        action="CREATE",
        entity_type="CHECKLIST_TEMPLATE",
        entity_id=template.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        after_data={
            **_template_audit_snapshot(template),
            "items": [item_payload.model_dump() for item_payload in payload.items],
        },
    )

    db.commit()
    db.refresh(template)
    return _template_to_public(template)


@router.get("", response_model=list[ChecklistTemplatePublic])
def list_templates(
    active_only: bool = Query(default=False),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    sector_id: int | None = Query(
        default=None,
        description="filtra pra checklists do setor informado OU sem setor (gestão) — usado pelo tablet.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChecklistTemplatePublic]:
    # Qualquer papel autenticado pode listar — o funcionário (tablet) e o
    # líder também precisam disso para escolher qual checklist iniciar.
    query = select(ChecklistTemplate)
    if current_user.role == "MASTER":
        if store_id is not None:
            query = query.where(ChecklistTemplate.store_id == store_id)
    else:
        query = query.where(ChecklistTemplate.store_id == current_user.store_id)

    if active_only:
        query = query.where(ChecklistTemplate.active.is_(True))
    if sector_id is not None:
        query = query.where(
            or_(ChecklistTemplate.target_sector_id == sector_id, ChecklistTemplate.target_sector_id.is_(None))
        )

    templates = db.scalars(query.order_by(ChecklistTemplate.name)).all()
    return [_template_to_public(template) for template in templates]


@router.get("/{template_id}", response_model=ChecklistTemplatePublic)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistTemplatePublic:
    template = _get_template_or_404(template_id, db)
    scope.require(template.store_id)
    return _template_to_public(template)


@router.patch("/{template_id}", response_model=ChecklistTemplatePublic)
def update_template(
    template_id: int,
    payload: ChecklistTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistTemplatePublic:
    template = _get_template_or_404(template_id, db)
    scope.require(template.store_id)

    updates = payload.model_dump(exclude_unset=True)
    if "target_sector_id" in updates and updates["target_sector_id"] is not None:
        _validate_sector_belongs_to_store(updates["target_sector_id"], template.store_id, db)

    before_data = _template_audit_snapshot(template)
    for field, value in updates.items():
        setattr(template, field, value)

    db.add(template)
    audit_service.log(
        db,
        store_id=template.store_id,
        action=audit_service.action_for_update(updates),
        entity_type="CHECKLIST_TEMPLATE",
        entity_id=template.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        before_data=before_data,
        after_data=_template_audit_snapshot(template),
    )
    db.commit()
    db.refresh(template)
    return _template_to_public(template)


@router.delete("/{template_id}", response_model=ChecklistTemplatePublic)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER")),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistTemplatePublic:
    template = _get_template_or_404(template_id, db)
    scope.require(template.store_id)

    if template.active:
        before_data = _template_audit_snapshot(template)
        template.active = False
        db.add(template)
        audit_service.log(
            db,
            store_id=template.store_id,
            action="DELETE",
            entity_type="CHECKLIST_TEMPLATE",
            entity_id=template.id,
            actor_user_id=current_user.id,
            actor_name=current_user.name,
            before_data=before_data,
            after_data=_template_audit_snapshot(template),
        )
        db.commit()
        db.refresh(template)

    return _template_to_public(template)


@router.post("/{template_id}/items", response_model=ChecklistTemplateItemPublic, status_code=status.HTTP_201_CREATED)
def create_template_item(
    template_id: int,
    payload: ChecklistTemplateItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistTemplateItemPublic:
    template = _get_template_or_404(template_id, db)
    scope.require(template.store_id)

    item = ChecklistTemplateItem(
        template_id=template.id,
        description=payload.description,
        order_index=payload.order_index,
        required=payload.required,
        requires_photo=payload.requires_photo,
    )
    db.add(item)
    db.flush()  # precisa do item.id para o audit log abaixo

    audit_service.log(
        db,
        store_id=template.store_id,
        action="CREATE",
        entity_type="CHECKLIST_TEMPLATE_ITEM",
        entity_id=item.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        after_data=_item_audit_snapshot(item),
    )

    db.commit()
    db.refresh(item)
    return _item_to_public(item)


@items_router.patch("/{item_id}", response_model=ChecklistTemplateItemPublic)
def update_template_item(
    item_id: int,
    payload: ChecklistTemplateItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistTemplateItemPublic:
    item = _get_item_or_404(item_id, db)
    template = _get_template_or_404(item.template_id, db)
    scope.require(template.store_id)

    updates = payload.model_dump(exclude_unset=True)
    before_data = _item_audit_snapshot(item)
    for field, value in updates.items():
        setattr(item, field, value)

    db.add(item)
    audit_service.log(
        db,
        store_id=template.store_id,
        action=audit_service.action_for_update(updates),
        entity_type="CHECKLIST_TEMPLATE_ITEM",
        entity_id=item.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        before_data=before_data,
        after_data=_item_audit_snapshot(item),
    )
    db.commit()
    db.refresh(item)
    return _item_to_public(item)
