from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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
from app.models.checklist import ChecklistExecution, ChecklistExecutionItem, ChecklistTemplate, ChecklistValidation
from app.models.employee import Employee
from app.models.user import User
from app.schemas.checklist_execution import (
    ChecklistExecutionCreate,
    ChecklistExecutionItemAnswerRequest,
    ChecklistExecutionItemPublic,
    ChecklistExecutionPublic,
    ChecklistItemPhotoUploadResponse,
    ChecklistValidationPublic,
    ChecklistValidationRequest,
)
from app.services import audit_service, checklist_service, photo_storage_service, store_settings_service

_MANAGE_ROLES = ("MASTER", "GESTOR", "LIDER")

router = APIRouter(prefix="/checklists", tags=["checklists"])

_EXECUTION_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist não encontrado.")
_ITEM_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item do checklist não encontrado.")


def _validation_to_public(validation: ChecklistValidation) -> ChecklistValidationPublic:
    return ChecklistValidationPublic(
        id=validation.id,
        checklist_execution_item_id=validation.checklist_execution_item_id,
        validated_by_user_id=validation.validated_by_user_id,
        validated_at=validation.validated_at,
        result=validation.result,
        justification=validation.justification,
        original_response_snapshot=validation.original_response_snapshot,
    )


def _item_to_public(item: ChecklistExecutionItem) -> ChecklistExecutionItemPublic:
    return ChecklistExecutionItemPublic(
        id=item.id,
        checklist_execution_id=item.checklist_execution_id,
        template_item_id=item.template_item_id,
        item_description_snapshot=item.item_description_snapshot,
        response=item.response,
        observation=item.observation,
        photo_url=item.photo_url,
        extra_photo_urls=item.extra_photo_urls,
        requires_photo=item.template_item.requires_photo,
        validation=_validation_to_public(item.validation) if item.validation else None,
    )


def _execution_to_public(execution: ChecklistExecution, db: Session) -> ChecklistExecutionPublic:
    items = sorted(execution.items, key=lambda item: item.id)
    fully_validated = all(item.validation is not None for item in items if item.response is not None)

    if execution.executed_by_user_id is not None:
        executor = db.get(User, execution.executed_by_user_id)
        executed_by_name = executor.name if executor is not None else "Usuário"
    else:
        executor_employee = db.get(Employee, execution.executed_by_employee_id)
        executed_by_name = executor_employee.name if executor_employee is not None else "Funcionário"

    validator_ids = {item.validation.validated_by_user_id for item in items if item.validation is not None}
    validators = [db.get(User, user_id) for user_id in validator_ids]
    validated_by_names = sorted(validator.name for validator in validators if validator is not None)

    return ChecklistExecutionPublic(
        id=execution.id,
        template_id=execution.template_id,
        template_name=execution.template.name,
        store_id=execution.store_id,
        shift=execution.shift,
        executed_by_user_id=execution.executed_by_user_id,
        executed_by_employee_id=execution.executed_by_employee_id,
        executed_by_name=executed_by_name,
        validated_by_names=validated_by_names,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        status=execution.status,
        fully_validated=fully_validated,
        items=[_item_to_public(item) for item in items],
    )


def _get_execution_or_404(execution_id: int, db: Session) -> ChecklistExecution:
    execution = db.get(ChecklistExecution, execution_id)
    if execution is None:
        raise _EXECUTION_NOT_FOUND
    return execution


def _get_item_or_404(execution: ChecklistExecution, item_id: int, db: Session) -> ChecklistExecutionItem:
    item = db.get(ChecklistExecutionItem, item_id)
    if item is None or item.checklist_execution_id != execution.id:
        raise _ITEM_NOT_FOUND
    return item


@router.post("", response_model=ChecklistExecutionPublic, status_code=status.HTTP_201_CREATED)
def start_execution(
    payload: ChecklistExecutionCreate,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistExecutionPublic:
    template = db.get(ChecklistTemplate, payload.template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template não encontrado.")
    scope.require(template.store_id)

    if not template.active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Este template de checklist está desativado.", "code": "TEMPLATE_INACTIVE"},
        )

    if payload.employee_id is not None or payload.pin is not None:
        if not store_settings_service.get_effective_settings(db, template.store_id).operational_checklists_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Checklists estão desativados para o operacional desta loja.",
                    "code": "CHECKLISTS_DISABLED_FOR_STORE",
                },
            )
        employee = require_pin_verified_employee(payload.employee_id, payload.pin, db, scope)
        if template.target_sector_id is not None and employee.sector_id != template.target_sector_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Este funcionário não pertence ao setor deste checklist.",
                    "code": "EMPLOYEE_NOT_IN_SECTOR",
                },
            )
        actor_kwargs: dict[str, int] = {"employee_id": employee.id}
        actor_name = employee.name
    else:
        if scope.user.role not in _MANAGE_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar este recurso.",
            )
        actor_kwargs = {"user_id": scope.user.id}
        actor_name = scope.user.name

    try:
        execution = checklist_service.start_execution(
            db, template, shift=payload.shift, actor_name=actor_name, **actor_kwargs
        )
    except checklist_service.ChecklistAlreadyInProgressError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Já existe um checklist em andamento para este template e turno hoje.",
                "code": "CHECKLIST_ALREADY_IN_PROGRESS",
            },
        ) from None

    return _execution_to_public(execution, db)


@router.get("", response_model=list[ChecklistExecutionPublic])
def list_executions(
    template_id: int | None = Query(default=None),
    shift: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    store_id: int | None = Query(default=None, description="Só considerado para o papel MASTER."),
    started_from: date | None = Query(default=None, description="Filtra started_at >= este dia (UTC), inclusive."),
    started_to: date | None = Query(default=None, description="Filtra started_at <= este dia (UTC), inclusive."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChecklistExecutionPublic]:
    query = select(ChecklistExecution)

    if current_user.role == "MASTER":
        if store_id is not None:
            query = query.where(ChecklistExecution.store_id == store_id)
    else:
        query = query.where(ChecklistExecution.store_id == current_user.store_id)

    if template_id is not None:
        query = query.where(ChecklistExecution.template_id == template_id)
    if shift is not None:
        query = query.where(ChecklistExecution.shift == shift)
    if status_filter is not None:
        query = query.where(ChecklistExecution.status == status_filter)
    # "Dia" aqui é o dia em UTC — mesma simplificação (e mesma limitação de
    # fuso) já documentada para task_assignments.day_of_week.
    if started_from is not None:
        query = query.where(ChecklistExecution.started_at >= datetime.combine(started_from, time.min, tzinfo=timezone.utc))
    if started_to is not None:
        query = query.where(ChecklistExecution.started_at <= datetime.combine(started_to, time.max, tzinfo=timezone.utc))

    executions = db.scalars(query.order_by(ChecklistExecution.started_at.desc())).all()
    return [_execution_to_public(execution, db) for execution in executions]


@router.get("/{execution_id}", response_model=ChecklistExecutionPublic)
def get_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistExecutionPublic:
    execution = _get_execution_or_404(execution_id, db)
    scope.require(execution.store_id)
    return _execution_to_public(execution, db)


@router.patch("/{execution_id}/items/{item_id}", response_model=ChecklistExecutionItemPublic)
def answer_item(
    execution_id: int,
    item_id: int,
    payload: ChecklistExecutionItemAnswerRequest,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistExecutionItemPublic:
    execution = _get_execution_or_404(execution_id, db)
    scope.require(execution.store_id)
    item = _get_item_or_404(execution, item_id, db)

    if execution.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Este checklist não está mais em andamento.", "code": "CHECKLIST_NOT_IN_PROGRESS"},
        )

    if item.template_item.requires_photo and payload.photo_url is None and item.photo_url is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Este item exige uma foto para ser respondido.", "code": "PHOTO_PROOF_REQUIRED"},
        )

    item.response = payload.response
    item.observation = payload.observation
    if payload.photo_url is not None:
        item.photo_url = payload.photo_url
    if payload.extra_photo_urls:
        item.extra_photo_urls = payload.extra_photo_urls
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_to_public(item)


@router.post("/{execution_id}/items/{item_id}/photo", response_model=ChecklistItemPhotoUploadResponse)
def upload_item_photo(
    execution_id: int,
    item_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistItemPhotoUploadResponse:
    execution = _get_execution_or_404(execution_id, db)
    scope.require(execution.store_id)
    _get_item_or_404(execution, item_id, db)

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

    return ChecklistItemPhotoUploadResponse(photo_url=photo_url)


@router.post("/{execution_id}/complete", response_model=ChecklistExecutionPublic)
def complete_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistExecutionPublic:
    execution = _get_execution_or_404(execution_id, db)
    scope.require(execution.store_id)

    try:
        execution = checklist_service.complete_execution(db, execution)
    except checklist_service.ChecklistNotInProgressError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Este checklist não está mais em andamento.", "code": "CHECKLIST_NOT_IN_PROGRESS"},
        ) from None
    except checklist_service.ChecklistIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Existem itens obrigatórios sem resposta.",
                "code": "CHECKLIST_INCOMPLETE",
                "missing_item_ids": exc.missing_item_ids,
            },
        ) from None

    return _execution_to_public(execution, db)


@router.post(
    "/{execution_id}/items/{item_id}/validate",
    response_model=ChecklistValidationPublic,
    status_code=status.HTTP_201_CREATED,
)
def validate_item(
    execution_id: int,
    item_id: int,
    payload: ChecklistValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    scope: StoreScope = Depends(get_current_store_scope),
) -> ChecklistValidationPublic:
    execution = _get_execution_or_404(execution_id, db)
    scope.require(execution.store_id)
    item = _get_item_or_404(execution, item_id, db)

    if execution.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Só é possível validar itens de um checklist já concluído.",
                "code": "CHECKLIST_NOT_COMPLETED",
            },
        )
    if item.response is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Este item não foi respondido — não há o que validar.", "code": "ITEM_NOT_ANSWERED"},
        )
    if item.validation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Este item já foi validado.", "code": "CHECKLIST_ITEM_ALREADY_VALIDATED"},
        )
    if execution.executed_by_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Quem executou o checklist não pode validar seus próprios itens.",
                "code": "SAME_USER_VALIDATION_FORBIDDEN",
            },
        )

    validation = ChecklistValidation(
        checklist_execution_item_id=item.id,
        store_id=execution.store_id,
        validated_by_user_id=current_user.id,
        result=payload.result,
        justification=payload.justification,
        original_response_snapshot={
            "item_description": item.item_description_snapshot,
            "response": item.response,
            "observation": item.observation,
        },
    )
    db.add(validation)
    db.flush()  # precisa do validation.id para o audit log abaixo

    audit_service.log(
        db,
        store_id=execution.store_id,
        action="VALIDATE",
        entity_type="CHECKLIST_VALIDATION",
        entity_id=validation.id,
        actor_user_id=current_user.id,
        actor_name=current_user.name,
        after_data={
            "checklist_execution_item_id": item.id,
            "result": validation.result,
            "justification": validation.justification,
        },
    )

    db.commit()
    db.refresh(validation)
    return _validation_to_public(validation)
