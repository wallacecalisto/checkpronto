from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import StoreScope, get_current_store_scope, get_current_user, require_roles, resolve_scoped_store_id
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskPublic, TaskUpdate
from app.services import audit_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

_MANAGE_ROLES = ("MASTER", "GESTOR", "LIDER")
_TASK_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada.")


def _to_public(task: Task) -> TaskPublic:
    return TaskPublic(
        id=task.id,
        store_id=task.store_id,
        title=task.title,
        description=task.description,
        estimated_duration_minutes=task.estimated_duration_minutes,
        requires_photo_proof=task.requires_photo_proof,
        active=task.active,
        created_by_user_id=task.created_by_user_id,
        created_at=task.created_at,
    )


def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise _TASK_NOT_FOUND
    return task


def _audit_snapshot(task: Task) -> dict:
    return {
        "title": task.title,
        "description": task.description,
        "estimated_duration_minutes": task.estimated_duration_minutes,
        "requires_photo_proof": task.requires_photo_proof,
        "active": task.active,
    }


@router.post("", response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
) -> TaskPublic:
    store_id = resolve_scoped_store_id(current_user, payload.store_id, db)

    task = Task(
        store_id=store_id,
        title=payload.title,
        description=payload.description,
        estimated_duration_minutes=payload.estimated_duration_minutes,
        requires_photo_proof=payload.requires_photo_proof,
        created_by_user_id=current_user.id,
    )
    db.add(task)
    db.flush()  # precisa do task.id para o audit log abaixo

    audit_service.log(
        db,
        store_id=store_id,
        action="CREATE",
        entity_type="TASK",
        entity_id=task.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        after_data=_audit_snapshot(task),
    )

    db.commit()
    db.refresh(task)
    return _to_public(task)


@router.get("", response_model=list[TaskPublic])
def list_tasks(
    active_only: bool = Query(default=False),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskPublic]:
    query = select(Task)

    if current_user.role == "MASTER":
        if store_id is not None:
            query = query.where(Task.store_id == store_id)
    else:
        query = query.where(Task.store_id == current_user.store_id)

    if active_only:
        query = query.where(Task.active.is_(True))

    tasks = db.scalars(query.order_by(Task.title)).all()
    return [_to_public(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskPublic)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskPublic:
    task = _get_task_or_404(task_id, db)
    scope.require(task.store_id)
    return _to_public(task)


@router.patch("/{task_id}", response_model=TaskPublic)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskPublic:
    task = _get_task_or_404(task_id, db)
    scope.require(task.store_id)

    updates = payload.model_dump(exclude_unset=True)

    before_data = _audit_snapshot(task)
    for field, value in updates.items():
        setattr(task, field, value)

    db.add(task)
    audit_service.log(
        db,
        store_id=task.store_id,
        action=audit_service.action_for_update(updates),
        entity_type="TASK",
        entity_id=task.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        before_data=before_data,
        after_data=_audit_snapshot(task),
    )
    db.commit()
    db.refresh(task)
    return _to_public(task)


@router.delete("/{task_id}", response_model=TaskPublic)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("MASTER")),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskPublic:
    task = _get_task_or_404(task_id, db)
    scope.require(task.store_id)

    if task.active:
        before_data = _audit_snapshot(task)
        task.active = False
        db.add(task)
        audit_service.log(
            db,
            store_id=task.store_id,
            action="DELETE",
            entity_type="TASK",
            entity_id=task.id,
            actor_user_id=current_user.id,
            actor_name=current_user.name,
            before_data=before_data,
            after_data=_audit_snapshot(task),
        )
        db.commit()
        db.refresh(task)

    return _to_public(task)
