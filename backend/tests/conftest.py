import uuid
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_secret
from app.db.session import get_db
from app.main import create_app
from app.models.audit_log import AuditLog
from app.models.checklist import (
    ChecklistExecution,
    ChecklistExecutionItem,
    ChecklistTemplate,
    ChecklistTemplateItem,
    ChecklistValidation,
)
from app.models.employee import Employee
from app.models.sector import Sector
from app.models.store import Store
from app.models.task import Task, TaskAssignment, TaskExecutionHistory
from app.models.task_execution_block import TaskExecutionBlock
from app.models.task_execution_session import TaskExecutionSession
from app.models.user import User

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _alembic_config() -> Config:
    assert settings.test_database_url, (
        "TEST_DATABASE_URL não está definido em backend/.env — "
        "veja backend/.env.example."
    )
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.test_database_url)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    cfg = _alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(apply_migrations: None, test_engine: Engine) -> Session:
    connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(
        bind=connection, autoflush=False, autocommit=False, join_transaction_mode="create_savepoint"
    )
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    from app.core.rate_limit import login_rate_limiter, pin_rate_limiter

    login_rate_limiter.reset()
    pin_rate_limiter.reset()


@pytest.fixture(autouse=True)
def _fake_photo_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import photo_storage_service

    monkeypatch.setattr(settings, "r2_account_id", "test-account")
    monkeypatch.setattr(settings, "r2_access_key_id", "test-access-key")
    monkeypatch.setattr(settings, "r2_secret_access_key", "test-secret-key")
    monkeypatch.setattr(settings, "r2_bucket_name", "test-bucket")
    monkeypatch.setattr(settings, "r2_public_base_url", "https://pub-test.r2.dev")

    class _FakeS3Client:
        def put_object(self, **kwargs) -> None:
            return None

    monkeypatch.setattr(photo_storage_service, "_client", _FakeS3Client())


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """Cliente de teste da API, com o banco trocado pela sessão transacional do teste."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session: Session):

    def _make_user(
        *,
        email: str = "usuario@kijapa.com",
        password: str = "SenhaForte123!",
        role: str = "GESTOR",
        store_id: int | None = None,
        active: bool = True,
        name: str = "Usuário de Teste",
        must_change_password: bool = False,
    ) -> User:
        user = User(
            store_id=store_id,
            name=name,
            email=email,
            password_hash=hash_secret(password),
            role=role,
            active=active,
            must_change_password=must_change_password,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make_user


@pytest.fixture()
def make_store(db_session: Session):
    """Fábrica de lojas para os testes — mesma lógica da `make_user`."""

    def _make_store(*, name: str = "Loja de Teste", brand: str | None = None, active: bool = True) -> Store:
        store = Store(name=name, brand=brand, active=active)
        db_session.add(store)
        db_session.commit()
        db_session.refresh(store)
        return store

    return _make_store


@pytest.fixture()
def make_sector(db_session: Session):

    def _make_sector(*, store_id: int, name: str = "Geral", active: bool = True) -> Sector:
        sector = Sector(store_id=store_id, name=name, active=active)
        db_session.add(sector)
        db_session.commit()
        db_session.refresh(sector)
        return sector

    return _make_sector


@pytest.fixture()
def make_employee(db_session: Session, make_sector):

    def _make_employee(
        *,
        store_id: int,
        sector_id: int | None = None,
        name: str = "Funcionário de Teste",
        role_title: str | None = None,
        active: bool = True,
        pin: str | None = None,
    ) -> Employee:
        resolved_sector_id = sector_id
        if resolved_sector_id is None:
            existing_sector = db_session.scalars(
                select(Sector).where(Sector.store_id == store_id).order_by(Sector.id)
            ).first()
            resolved_sector_id = existing_sector.id if existing_sector is not None else make_sector(store_id=store_id).id

        employee = Employee(
            store_id=store_id,
            sector_id=resolved_sector_id,
            name=name,
            role_title=role_title,
            active=active,
            pin_hash=hash_secret(pin) if pin is not None else None,
        )
        db_session.add(employee)
        db_session.commit()
        db_session.refresh(employee)
        return employee

    return _make_employee


@pytest.fixture()
def make_task(db_session: Session):

    def _make_task(
        *,
        store_id: int,
        created_by_user_id: int,
        title: str = "Tarefa de Teste",
        description: str | None = None,
        estimated_duration_minutes: int | None = None,
        requires_photo_proof: bool = False,
        active: bool = True,
    ) -> Task:
        task = Task(
            store_id=store_id,
            title=title,
            description=description,
            estimated_duration_minutes=estimated_duration_minutes,
            requires_photo_proof=requires_photo_proof,
            active=active,
            created_by_user_id=created_by_user_id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    return _make_task


@pytest.fixture()
def make_task_assignment(db_session: Session, make_sector):

    def _make_task_assignment(
        *,
        task: Task,
        day_of_week: str = "MONDAY",
        sector_id: int | None = None,
        shift: str = "Geral",
        status: str = "PENDING",
        started_at=None,
        completed_at=None,
        started_by_employee_id: int | None = None,
        completed_by_employee_id: int | None = None,
        started_by_user_id: int | None = None,
        completed_by_user_id: int | None = None,
        result: str | None = None,
        justification: str | None = None,
        observation: str | None = None,
        photo_url: str | None = None,
        blocked_at=None,
        block_reason: str | None = None,
        blocked_by_employee_id: int | None = None,
    ) -> TaskAssignment:
        resolved_sector_id = sector_id
        if resolved_sector_id is None:
            existing_sector = db_session.scalars(
                select(Sector).where(Sector.store_id == task.store_id).order_by(Sector.id)
            ).first()
            resolved_sector_id = (
                existing_sector.id if existing_sector is not None else make_sector(store_id=task.store_id).id
            )

        assignment = TaskAssignment(
            task_id=task.id,
            store_id=task.store_id,
            day_of_week=day_of_week,
            sector_id=resolved_sector_id,
            shift=shift,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            started_by_employee_id=started_by_employee_id,
            completed_by_employee_id=completed_by_employee_id,
            started_by_user_id=started_by_user_id,
            completed_by_user_id=completed_by_user_id,
            result=result,
            justification=justification,
            observation=observation,
            photo_url=photo_url,
            blocked_at=blocked_at,
            block_reason=block_reason,
            blocked_by_employee_id=blocked_by_employee_id,
        )
        db_session.add(assignment)
        db_session.commit()
        db_session.refresh(assignment)
        return assignment

    return _make_task_assignment


@pytest.fixture()
def make_task_execution_session(db_session: Session):

    def _make_task_execution_session(
        *,
        assignment: TaskAssignment,
        employee_id: int,
        started_at,
        ended_at=None,
        leave_reason: str | None = None,
    ) -> TaskExecutionSession:
        session = TaskExecutionSession(
            task_assignment_id=assignment.id,
            employee_id=employee_id,
            store_id=assignment.store_id,
            started_at=started_at,
            ended_at=ended_at,
            leave_reason=leave_reason,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    return _make_task_execution_session


@pytest.fixture()
def make_task_execution_block(db_session: Session):

    def _make_task_execution_block(
        *,
        assignment: TaskAssignment,
        blocked_by_employee_id: int,
        reason: str,
        started_at,
        ended_at=None,
        execution_group_id: uuid.UUID | None = None,
    ) -> TaskExecutionBlock:
        block = TaskExecutionBlock(
            task_assignment_id=assignment.id,
            store_id=assignment.store_id,
            blocked_by_employee_id=blocked_by_employee_id,
            reason=reason,
            started_at=started_at,
            ended_at=ended_at,
            execution_group_id=execution_group_id,
        )
        db_session.add(block)
        db_session.commit()
        db_session.refresh(block)
        return block

    return _make_task_execution_block


@pytest.fixture()
def make_task_execution_history(db_session: Session):

    def _make_task_execution_history(
        *,
        store_id: int,
        task_id: int,
        employee_id: int,
        task_title: str = "Tarefa de Teste",
        started_at: datetime,
        completed_at: datetime,
        result: str = "FEITO",
        estimated_duration_minutes: int | None = None,
        justification: str | None = None,
        observation: str | None = None,
        photo_url: str | None = None,
        worked_duration_seconds: int | None = None,
        execution_group_id: uuid.UUID | None = None,
    ) -> TaskExecutionHistory:
        resolved_worked_duration_seconds = (
            worked_duration_seconds
            if worked_duration_seconds is not None
            else int((completed_at - started_at).total_seconds())
        )
        history = TaskExecutionHistory(
            store_id=store_id,
            task_id=task_id,
            task_title=task_title,
            employee_id=employee_id,
            started_at=started_at,
            completed_at=completed_at,
            result=result,
            estimated_duration_minutes=estimated_duration_minutes,
            justification=justification,
            observation=observation,
            photo_url=photo_url,
            worked_duration_seconds=resolved_worked_duration_seconds,
            execution_group_id=execution_group_id or uuid.uuid4(),
        )
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)
        return history

    return _make_task_execution_history


@pytest.fixture()
def make_checklist_template(db_session: Session):

    def _make_checklist_template(
        *,
        store_id: int,
        created_by_user_id: int,
        name: str = "Checklist de Teste",
        active: bool = True,
        target_sector_id: int | None = None,
        shift: str = "Geral",
    ) -> ChecklistTemplate:
        template = ChecklistTemplate(
            store_id=store_id,
            name=name,
            active=active,
            created_by_user_id=created_by_user_id,
            target_sector_id=target_sector_id,
            shift=shift,
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)
        return template

    return _make_checklist_template


@pytest.fixture()
def make_checklist_template_item(db_session: Session):
    """Fábrica de itens de um template."""

    def _make_checklist_template_item(
        *,
        template: ChecklistTemplate,
        description: str = "Item de Teste",
        order_index: int = 0,
        required: bool = True,
        requires_photo: bool = False,
        active: bool = True,
    ) -> ChecklistTemplateItem:
        item = ChecklistTemplateItem(
            template_id=template.id,
            description=description,
            order_index=order_index,
            required=required,
            requires_photo=requires_photo,
            active=active,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        return item

    return _make_checklist_template_item


@pytest.fixture()
def make_checklist_execution(db_session: Session):

    def _make_checklist_execution(
        *,
        template: ChecklistTemplate,
        executed_by_user_id: int | None = None,
        executed_by_employee_id: int | None = None,
        shift: str = "MANHA",
        status: str = "IN_PROGRESS",
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> ChecklistExecution:
        if executed_by_user_id is None and executed_by_employee_id is None:
            raise ValueError("Informe executed_by_user_id OU executed_by_employee_id.")
        execution = ChecklistExecution(
            template_id=template.id,
            store_id=template.store_id,
            shift=shift,
            status=status,
            executed_by_user_id=executed_by_user_id,
            executed_by_employee_id=executed_by_employee_id,
            finished_at=finished_at,
        )
        if started_at is not None:
            execution.started_at = started_at
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)
        return execution

    return _make_checklist_execution


@pytest.fixture()
def make_checklist_execution_item(db_session: Session):

    def _make_checklist_execution_item(
        *,
        execution: ChecklistExecution,
        template_item: ChecklistTemplateItem,
        item_description_snapshot: str | None = None,
        response: str | None = None,
        observation: str | None = None,
        photo_url: str | None = None,
    ) -> ChecklistExecutionItem:
        item = ChecklistExecutionItem(
            checklist_execution_id=execution.id,
            template_item_id=template_item.id,
            store_id=execution.store_id,
            item_description_snapshot=item_description_snapshot or template_item.description,
            response=response,
            observation=observation,
            photo_url=photo_url,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        return item

    return _make_checklist_execution_item


@pytest.fixture()
def make_checklist_validation(db_session: Session):
    def _make_checklist_validation(
        *,
        execution_item: ChecklistExecutionItem,
        validated_by_user_id: int,
        result: str = "APROVADO",
        justification: str | None = None,
        original_response_snapshot: dict | None = None,
        validated_at: datetime | None = None,
    ) -> ChecklistValidation:
        validation = ChecklistValidation(
            checklist_execution_item_id=execution_item.id,
            store_id=execution_item.store_id,
            validated_by_user_id=validated_by_user_id,
            result=result,
            justification=justification,
            original_response_snapshot=original_response_snapshot
            or {
                "item_description": execution_item.item_description_snapshot,
                "response": execution_item.response,
                "observation": execution_item.observation,
            },
        )
        if validated_at is not None:
            validation.validated_at = validated_at
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)
        return validation

    return _make_checklist_validation


@pytest.fixture()
def make_audit_log(db_session: Session):

    def _make_audit_log(
        *,
        store_id: int | None,
        action: str,
        entity_type: str,
        entity_id: int,
        actor_name: str,
        actor_user_id: int | None = None,
        actor_employee_id: int | None = None,
        before_data: dict | None = None,
        after_data: dict | None = None,
        created_at: datetime | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            store_id=store_id,
            actor_type="USER" if actor_user_id is not None else "EMPLOYEE",
            actor_user_id=actor_user_id,
            actor_employee_id=actor_employee_id,
            actor_name=actor_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_data=before_data,
            after_data=after_data,
        )
        if created_at is not None:
            entry.created_at = created_at
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)
        return entry

    return _make_audit_log


@pytest.fixture()
def auth_headers(client: TestClient):

    def _auth_headers(email: str, password: str) -> dict[str, str]:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers
