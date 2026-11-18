from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import (
    StoreScope,
    get_current_store_scope,
    get_current_user,
    require_pin_verified_employee,
    require_roles,
)
from app.db.session import get_db
from app.models.employee import Employee
from app.models.sector import Sector
from app.models.task import Task, TaskAssignment, TaskExecutionHistory
from app.models.task_execution_block import TaskExecutionBlock
from app.models.task_execution_session import TaskExecutionSession
from app.models.user import User
from app.schemas.task_assignment import (
    TaskAssignmentActionRequest,
    TaskAssignmentBlockRequest,
    TaskAssignmentCompleteRequest,
    TaskAssignmentCreate,
    TaskAssignmentLeaveRequest,
    TaskAssignmentParticipant,
    TaskAssignmentPhotoUploadResponse,
    TaskAssignmentPublic,
    TaskAssignmentUpdate,
)
from app.services import audit_service, photo_storage_service, task_assignment_service

router = APIRouter(prefix="/task-assignments", tags=["task-assignments"])

_MANAGE_ROLES = ("MASTER", "GESTOR", "LIDER")
_ASSIGNMENT_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento não encontrado.")
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


def _active_participants(assignment: TaskAssignment, db: Session) -> list[TaskAssignmentParticipant]:
    if assignment.status != "IN_PROGRESS":
        return []
    rows = db.execute(
        select(TaskExecutionSession, Employee.name)
        .join(Employee, Employee.id == TaskExecutionSession.employee_id)
        .where(TaskExecutionSession.task_assignment_id == assignment.id)
        .where(TaskExecutionSession.ended_at.is_(None))
        .order_by(TaskExecutionSession.started_at)
    )
    return [
        TaskAssignmentParticipant(employee_id=session.employee_id, employee_name=name, started_at=session.started_at)
        for session, name in rows
    ]


def _latest_execution_history_id(assignment: TaskAssignment, db: Session) -> int | None:
    if assignment.status != "COMPLETED" or assignment.completed_at is None:
        return None
    return db.scalar(
        select(TaskExecutionHistory.id)
        .where(
            TaskExecutionHistory.task_id == assignment.task_id,
            TaskExecutionHistory.store_id == assignment.store_id,
            TaskExecutionHistory.completed_at == assignment.completed_at,
        )
        .order_by(TaskExecutionHistory.id)
        .limit(1)
    )


def _total_paused_seconds(assignment: TaskAssignment, db: Session, reference: datetime) -> int:
    if assignment.started_at is None:
        return 0
    blocks = db.scalars(
        select(TaskExecutionBlock)
        .where(TaskExecutionBlock.task_assignment_id == assignment.id)
        .where(TaskExecutionBlock.started_at >= assignment.started_at)
        .where(TaskExecutionBlock.ended_at.is_not(None))
        .where(TaskExecutionBlock.ended_at <= reference)
    )
    return int(sum((block.ended_at - block.started_at).total_seconds() for block in blocks))


def _to_public(assignment: TaskAssignment, db: Session) -> TaskAssignmentPublic:
    elapsed_seconds = None
    if assignment.started_at is not None:
        if assignment.status == "BLOCKED" and assignment.blocked_at is not None:
            reference = assignment.blocked_at
        else:
            reference = assignment.completed_at or datetime.now(timezone.utc)
        elapsed_seconds = int((reference - assignment.started_at).total_seconds())
        elapsed_seconds -= _total_paused_seconds(assignment, db, reference)

    return TaskAssignmentPublic(
        id=assignment.id,
        task_id=assignment.task_id,
        store_id=assignment.store_id,
        day_of_week=assignment.day_of_week,
        task_title=assignment.task.title,
        task_description=assignment.task.description,
        estimated_duration_minutes=assignment.task.estimated_duration_minutes,
        requires_photo_proof=assignment.task.requires_photo_proof,
        shift=assignment.shift,
        sector_id=assignment.sector_id,
        sector_name=assignment.sector.name,
        status=assignment.status,
        started_at=assignment.started_at,
        completed_at=assignment.completed_at,
        started_by_employee_id=assignment.started_by_employee_id,
        completed_by_employee_id=assignment.completed_by_employee_id,
        started_by_user_id=assignment.started_by_user_id,
        completed_by_user_id=assignment.completed_by_user_id,
        result=assignment.result,
        justification=assignment.justification,
        observation=assignment.observation,
        photo_url=assignment.photo_url,
        extra_photo_urls=assignment.extra_photo_urls,
        elapsed_seconds=elapsed_seconds,
        active_participants=_active_participants(assignment, db),
        blocked_at=assignment.blocked_at,
        block_reason=assignment.block_reason,
        blocked_by_employee_id=assignment.blocked_by_employee_id,
        latest_execution_history_id=_latest_execution_history_id(assignment, db),
    )


def _get_assignment_or_404(assignment_id: int, db: Session) -> TaskAssignment:
    assignment = db.get(TaskAssignment, assignment_id)
    if assignment is None:
        raise _ASSIGNMENT_NOT_FOUND
    return assignment


def _audit_snapshot(assignment: TaskAssignment) -> dict:
    return {"day_of_week": assignment.day_of_week, "sector_id": assignment.sector_id, "shift": assignment.shift}


# --- CRUD -----------------------------------------------------------------------


@router.post("", response_model=TaskAssignmentPublic, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: TaskAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    task = db.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada no catálogo.")
    scope.require(task.store_id)

    if not task.active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Esta tarefa do catálogo está desativada.", "code": "TASK_INACTIVE"},
        )

    _validate_sector_belongs_to_store(payload.sector_id, task.store_id, db)

    assignment = TaskAssignment(
        task_id=task.id,
        store_id=task.store_id,
        day_of_week=payload.day_of_week,
        sector_id=payload.sector_id,
        shift=payload.shift,
    )
    db.add(assignment)
    db.flush()  # precisa do assignment.id para o audit log abaixo

    audit_service.log(
        db,
        store_id=task.store_id,
        action="CREATE",
        entity_type="TASK_ASSIGNMENT",
        entity_id=assignment.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        after_data=_audit_snapshot(assignment),
    )

    db.commit()
    db.refresh(assignment)
    return _to_public(assignment, db)


@router.get("", response_model=list[TaskAssignmentPublic])
def list_assignments(
    day_of_week: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    sector_id: int | None = Query(default=None),
    shift: str | None = Query(default=None),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskAssignmentPublic]:
    query = select(TaskAssignment).join(Task, TaskAssignment.task_id == Task.id).where(Task.active.is_(True))

    if current_user.role == "MASTER":
        if store_id is not None:
            query = query.where(TaskAssignment.store_id == store_id)
    else:
        query = query.where(TaskAssignment.store_id == current_user.store_id)

    if day_of_week is not None:
        query = query.where(TaskAssignment.day_of_week == day_of_week)
    if status_filter is not None:
        query = query.where(TaskAssignment.status == status_filter)
    if sector_id is not None:
        query = query.where(TaskAssignment.sector_id == sector_id)
    if shift is not None:
        query = query.where(TaskAssignment.shift == shift)

    assignments = list(db.scalars(query.order_by(TaskAssignment.day_of_week, TaskAssignment.id)))
    task_assignment_service.apply_weekly_reset_bulk(db, assignments)

    return [_to_public(assignment, db) for assignment in assignments]


@router.get("/{assignment_id}", response_model=TaskAssignmentPublic)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)
    if task_assignment_service.apply_weekly_reset(db, assignment):
        db.commit()
    return _to_public(assignment, db)


@router.patch("/{assignment_id}", response_model=TaskAssignmentPublic)
def update_assignment(
    assignment_id: int,
    payload: TaskAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)

    if payload.sector_id is not None:
        _validate_sector_belongs_to_store(payload.sector_id, assignment.store_id, db)

    before_data = _audit_snapshot(assignment)
    if payload.day_of_week is not None:
        assignment.day_of_week = payload.day_of_week
    if payload.sector_id is not None:
        assignment.sector_id = payload.sector_id
    if payload.shift is not None:
        assignment.shift = payload.shift

    db.add(assignment)
    audit_service.log(
        db,
        store_id=assignment.store_id,
        action="UPDATE",
        entity_type="TASK_ASSIGNMENT",
        entity_id=assignment.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        before_data=before_data,
        after_data=_audit_snapshot(assignment),
    )
    db.commit()
    db.refresh(assignment)
    return _to_public(assignment, db)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> None:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)

    audit_service.log(
        db,
        store_id=assignment.store_id,
        action="DELETE",
        entity_type="TASK_ASSIGNMENT",
        entity_id=assignment.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        before_data=_audit_snapshot(assignment),
    )

    db.delete(assignment)
    db.commit()


# --- transições de estado ---------------------------------------------------------


@router.post("/{assignment_id}/start", response_model=TaskAssignmentPublic)
def start_assignment(
    assignment_id: int,
    payload: TaskAssignmentActionRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)
    if task_assignment_service.apply_weekly_reset(db, assignment):
        db.commit()

    employee = require_pin_verified_employee(payload.employee_id, payload.pin, db, scope)

    try:
        assignment = task_assignment_service.start_assignment(db, assignment, employee=employee)
    except task_assignment_service.EmployeeNotInSectorError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Este funcionário não pertence ao setor desta tarefa.",
                "code": "EMPLOYEE_NOT_IN_SECTOR",
            },
        ) from None
    except task_assignment_service.TaskAssignmentNotPendingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "O agendamento não está pendente.", "code": "TASK_NOT_PENDING"},
        ) from None
    except task_assignment_service.EmployeeHasActiveTaskError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Você já tem uma tarefa em andamento. Conclua-a (ou saia dela) antes de iniciar outra.",
                "code": "EMPLOYEE_HAS_ACTIVE_TASK",
            },
        ) from None

    db.commit()
    return _to_public(assignment, db)


@router.post("/{assignment_id}/join", response_model=TaskAssignmentPublic)
def join_assignment(
    assignment_id: int,
    payload: TaskAssignmentActionRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)
    if task_assignment_service.apply_weekly_reset(db, assignment):
        db.commit()

    employee = require_pin_verified_employee(payload.employee_id, payload.pin, db, scope)

    try:
        assignment = task_assignment_service.join_assignment(db, assignment, employee=employee)
    except task_assignment_service.EmployeeNotInSectorError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Este funcionário não pertence ao setor desta tarefa.",
                "code": "EMPLOYEE_NOT_IN_SECTOR",
            },
        ) from None
    except task_assignment_service.TaskAssignmentNotInProgressError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "O agendamento não está em andamento.", "code": "TASK_NOT_IN_PROGRESS"},
        ) from None
    except task_assignment_service.EmployeeAlreadyInTaskError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Você já está nesta tarefa.", "code": "EMPLOYEE_ALREADY_IN_TASK"},
        ) from None
    except task_assignment_service.MaxAssigneesReachedError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Esta tarefa já atingiu o número máximo de funcionários simultâneos configurado para a loja.",
                "code": "MAX_ASSIGNEES_REACHED",
            },
        ) from None
    except task_assignment_service.EmployeeHasActiveTaskError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Você já tem uma tarefa em andamento. Conclua-a (ou saia dela) antes de entrar em outra.",
                "code": "EMPLOYEE_HAS_ACTIVE_TASK",
            },
        ) from None

    db.commit()
    return _to_public(assignment, db)


@router.post("/{assignment_id}/leave", response_model=TaskAssignmentPublic)
def leave_assignment(
    assignment_id: int,
    payload: TaskAssignmentLeaveRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)

    employee = require_pin_verified_employee(payload.employee_id, payload.pin, db, scope)

    try:
        assignment = task_assignment_service.leave_assignment(
            db, assignment, employee_id=employee.id, leave_reason=payload.leave_reason
        )
    except task_assignment_service.NoActiveSessionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Você não está nesta tarefa agora.", "code": "NO_ACTIVE_SESSION"},
        ) from None

    db.commit()
    return _to_public(assignment, db)


@router.post("/{assignment_id}/complete", response_model=TaskAssignmentPublic)
def complete_assignment(
    assignment_id: int,
    payload: TaskAssignmentCompleteRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)
    if task_assignment_service.apply_weekly_reset(db, assignment):
        db.commit()

    employee = require_pin_verified_employee(payload.employee_id, payload.pin, db, scope)

    try:
        assignment = task_assignment_service.complete_assignment(
            db,
            assignment,
            result=payload.result,
            justification=payload.justification,
            observation=payload.observation,
            photo_url=payload.photo_url,
            extra_photo_urls=payload.extra_photo_urls,
            employee=employee,
        )
    except task_assignment_service.EmployeeNotInSectorError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Este funcionário não pertence ao setor desta tarefa.",
                "code": "EMPLOYEE_NOT_IN_SECTOR",
            },
        ) from None
    except task_assignment_service.EmployeeNotParticipatingError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Você precisa estar participando da tarefa para concluí-la.",
                "code": "EMPLOYEE_NOT_PARTICIPATING",
            },
        ) from None
    except task_assignment_service.TaskAssignmentNotInProgressError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "O agendamento não está em andamento.", "code": "TASK_NOT_IN_PROGRESS"},
        ) from None
    except task_assignment_service.PhotoProofRequiredError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Esta tarefa exige uma foto para ser concluída como Feito.",
                "code": "PHOTO_PROOF_REQUIRED",
            },
        ) from None

    db.commit()
    return _to_public(assignment, db)


@router.post("/{assignment_id}/photo", response_model=TaskAssignmentPhotoUploadResponse)
def upload_assignment_photo(
    assignment_id: int,
    employee_id: int = Form(...),
    pin: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPhotoUploadResponse:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)
    require_pin_verified_employee(employee_id, pin, db, scope)

    try:
        photo_url = photo_storage_service.upload_task_photo(photo)
    except photo_storage_service.InvalidPhotoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(exc), "code": "INVALID_PHOTO"},
        ) from None
    except (photo_storage_service.PhotoStorageConfigError, photo_storage_service.PhotoUploadFailedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": str(exc), "code": "PHOTO_UPLOAD_FAILED"},
        ) from None

    return TaskAssignmentPhotoUploadResponse(photo_url=photo_url)


@router.post("/{assignment_id}/block", response_model=TaskAssignmentPublic)
def block_assignment(
    assignment_id: int,
    payload: TaskAssignmentBlockRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)
    if task_assignment_service.apply_weekly_reset(db, assignment):
        db.commit()

    employee = require_pin_verified_employee(payload.employee_id, payload.pin, db, scope)

    try:
        assignment = task_assignment_service.block_assignment(
            db, assignment, employee=employee, reason=payload.reason
        )
    except task_assignment_service.EmployeeNotInSectorError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Este funcionário não pertence ao setor desta tarefa.",
                "code": "EMPLOYEE_NOT_IN_SECTOR",
            },
        ) from None
    except task_assignment_service.TaskAssignmentNotInProgressError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "O agendamento não está em andamento.", "code": "TASK_NOT_IN_PROGRESS"},
        ) from None

    db.commit()
    return _to_public(assignment, db)


@router.post("/{assignment_id}/resume", response_model=TaskAssignmentPublic)
def resume_assignment(
    assignment_id: int,
    payload: TaskAssignmentActionRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> TaskAssignmentPublic:
    assignment = _get_assignment_or_404(assignment_id, db)
    scope.require(assignment.store_id)

    employee = require_pin_verified_employee(payload.employee_id, payload.pin, db, scope)

    try:
        assignment = task_assignment_service.resume_assignment(db, assignment, employee=employee)
    except task_assignment_service.EmployeeNotInSectorError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Este funcionário não pertence ao setor desta tarefa.",
                "code": "EMPLOYEE_NOT_IN_SECTOR",
            },
        ) from None
    except task_assignment_service.TaskAssignmentNotBlockedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "O agendamento não está impedido.", "code": "TASK_NOT_BLOCKED"},
        ) from None
    except task_assignment_service.EmployeeHasActiveTaskError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Você já tem uma tarefa em andamento. Conclua-a (ou saia dela) antes de retomar outra.",
                "code": "EMPLOYEE_HAS_ACTIVE_TASK",
            },
        ) from None

    db.commit()
    return _to_public(assignment, db)
