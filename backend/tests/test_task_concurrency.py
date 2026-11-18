
import threading
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_secret
from app.models.employee import Employee
from app.models.sector import Sector
from app.models.store import Store
from app.models.task import DAYS_OF_WEEK, Task, TaskAssignment
from app.models.task_execution_session import TaskExecutionSession
from app.models.user import User
from app.services import task_assignment_service


def test_two_employees_cannot_start_the_same_assignment_at_the_same_time() -> None:
    engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    setup = SessionLocal()
    try:
        store = Store(name="Loja Concorrência")
        setup.add(store)
        setup.commit()
        setup.refresh(store)

        manager = User(
            store_id=store.id,
            name="Gestor",
            email="concorrencia-gestor@kijapa.com",
            password_hash=hash_secret("SenhaForte123!"),
            role="GESTOR",
            active=True,
        )
        setup.add(manager)
        setup.commit()
        setup.refresh(manager)

        sector = Sector(store_id=store.id, name="Geral")
        setup.add(sector)
        setup.commit()
        setup.refresh(sector)

        employee_a = Employee(store_id=store.id, sector_id=sector.id, name="Funcionário A")
        employee_b = Employee(store_id=store.id, sector_id=sector.id, name="Funcionário B")
        setup.add_all([employee_a, employee_b])
        setup.commit()
        setup.refresh(employee_a)
        setup.refresh(employee_b)

        task = Task(
            store_id=store.id,
            title="Tarefa disputada",
            created_by_user_id=manager.id,
        )
        setup.add(task)
        setup.commit()
        setup.refresh(task)

        today_day_of_week = DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]
        assignment = TaskAssignment(
            task_id=task.id,
            store_id=store.id,
            day_of_week=today_day_of_week,
            sector_id=sector.id,
            shift="Geral",
            status="PENDING",
        )
        setup.add(assignment)
        setup.commit()
        setup.refresh(assignment)

        assignment_id = assignment.id
        employee_a_id = employee_a.id
        employee_b_id = employee_b.id
        store_id = store.id
        task_id = task.id
        manager_id = manager.id
        sector_id = sector.id
    finally:
        setup.close()

    # Cada thread abre a SUA PRÓPRIA sessão/conexão — como duas requisições HTTP
    # de verdade chegando ao mesmo tempo, cada uma com sua conexão do pool.
    barrier = threading.Barrier(2)
    results: dict[str, str] = {}

    def attempt_start(name: str, employee_id: int) -> None:
        session = SessionLocal()
        try:
            local_assignment = session.get(TaskAssignment, assignment_id)
            local_employee = session.get(Employee, employee_id)
            barrier.wait(timeout=5)  # maximiza a chance das duas UPDATEs colidirem de verdade
            try:
                task_assignment_service.start_assignment(session, local_assignment, employee=local_employee)
                session.commit()
                results[name] = "success"
            except task_assignment_service.TaskAssignmentNotPendingError:
                session.rollback()
                results[name] = "rejected"
        finally:
            session.close()

    thread_a = threading.Thread(target=attempt_start, args=("A", employee_a_id))
    thread_b = threading.Thread(target=attempt_start, args=("B", employee_b_id))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)

    try:
        # Exatamente um dos dois venceu a corrida — nunca os dois, nunca nenhum.
        assert sorted(results.values()) == ["rejected", "success"], results

        verify = SessionLocal()
        try:
            final_assignment = verify.get(TaskAssignment, assignment_id)
            assert final_assignment.status == "IN_PROGRESS"
            assert final_assignment.started_by_employee_id in (employee_a_id, employee_b_id)
        finally:
            verify.close()
    finally:
        # Limpeza manual — este teste não roda dentro do rollback padrão.
        cleanup = SessionLocal()
        try:
            cleanup.query(TaskExecutionSession).filter(TaskExecutionSession.store_id == store_id).delete()
            cleanup.query(TaskAssignment).filter(TaskAssignment.store_id == store_id).delete()
            cleanup.query(Task).filter(Task.id == task_id).delete()
            cleanup.query(Employee).filter(Employee.store_id == store_id).delete()
            cleanup.query(Sector).filter(Sector.id == sector_id).delete()
            cleanup.query(User).filter(User.id == manager_id).delete()
            cleanup.query(Store).filter(Store.id == store_id).delete()
            cleanup.commit()
        finally:
            cleanup.close()
        engine.dispose()


def test_two_employees_of_the_same_sector_can_join_the_same_task_at_the_same_time() -> None:
    engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    setup = SessionLocal()
    try:
        store = Store(name="Loja Colaboração")
        setup.add(store)
        setup.commit()
        setup.refresh(store)

        manager = User(
            store_id=store.id,
            name="Gestor",
            email="colaboracao-gestor@kijapa.com",
            password_hash=hash_secret("SenhaForte123!"),
            role="GESTOR",
            active=True,
        )
        setup.add(manager)
        setup.commit()
        setup.refresh(manager)

        sector = Sector(store_id=store.id, name="Geral")
        setup.add(sector)
        setup.commit()
        setup.refresh(sector)

        employee_starter = Employee(store_id=store.id, sector_id=sector.id, name="Quem iniciou")
        employee_b = Employee(store_id=store.id, sector_id=sector.id, name="Funcionário B")
        employee_c = Employee(store_id=store.id, sector_id=sector.id, name="Funcionário C")
        setup.add_all([employee_starter, employee_b, employee_c])
        setup.commit()
        setup.refresh(employee_starter)
        setup.refresh(employee_b)
        setup.refresh(employee_c)

        task = Task(store_id=store.id, title="Tarefa colaborativa", created_by_user_id=manager.id)
        setup.add(task)
        setup.commit()
        setup.refresh(task)

        today_day_of_week = DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]
        assignment = TaskAssignment(
            task_id=task.id,
            store_id=store.id,
            day_of_week=today_day_of_week,
            sector_id=sector.id,
            shift="Geral",
            status="PENDING",
        )
        setup.add(assignment)
        setup.commit()
        setup.refresh(assignment)

        task_assignment_service.start_assignment(setup, assignment, employee=employee_starter)
        setup.commit()

        assignment_id = assignment.id
        employee_starter_id = employee_starter.id
        employee_b_id = employee_b.id
        employee_c_id = employee_c.id
        store_id = store.id
        task_id = task.id
        manager_id = manager.id
        sector_id = sector.id
    finally:
        setup.close()

    barrier = threading.Barrier(2)
    results: dict[str, str] = {}

    def attempt_join(name: str, employee_id: int) -> None:
        session = SessionLocal()
        try:
            local_assignment = session.get(TaskAssignment, assignment_id)
            local_employee = session.get(Employee, employee_id)
            barrier.wait(timeout=5)
            try:
                task_assignment_service.join_assignment(session, local_assignment, employee=local_employee)
                session.commit()
                results[name] = "success"
            except Exception:
                session.rollback()
                results[name] = "rejected"
        finally:
            session.close()

    thread_b = threading.Thread(target=attempt_join, args=("B", employee_b_id))
    thread_c = threading.Thread(target=attempt_join, args=("C", employee_c_id))
    thread_b.start()
    thread_c.start()
    thread_b.join(timeout=10)
    thread_c.join(timeout=10)

    try:
        # As DUAS entradas simultâneas têm sucesso — não é uma disputa, é
        # exatamente o que "colaborativo" significa.
        assert results == {"B": "success", "C": "success"}, results

        verify = SessionLocal()
        try:
            open_sessions = (
                verify.query(TaskExecutionSession)
                .filter(
                    TaskExecutionSession.task_assignment_id == assignment_id,
                    TaskExecutionSession.ended_at.is_(None),
                )
                .all()
            )
            # O funcionário que iniciou a tarefa (fora das threads, no setup)
            # também continua com sessão aberta — os TRÊS coexistem.
            assert {session.employee_id for session in open_sessions} == {
                employee_starter_id,
                employee_b_id,
                employee_c_id,
            }
        finally:
            verify.close()
    finally:
        cleanup = SessionLocal()
        try:
            cleanup.query(TaskExecutionSession).filter(TaskExecutionSession.store_id == store_id).delete()
            cleanup.query(TaskAssignment).filter(TaskAssignment.store_id == store_id).delete()
            cleanup.query(Task).filter(Task.id == task_id).delete()
            cleanup.query(Employee).filter(Employee.store_id == store_id).delete()
            cleanup.query(Sector).filter(Sector.id == sector_id).delete()
            cleanup.query(User).filter(User.id == manager_id).delete()
            cleanup.query(Store).filter(Store.id == store_id).delete()
            cleanup.commit()
        finally:
            cleanup.close()
        engine.dispose()
