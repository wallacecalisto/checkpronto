
import threading

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.store import Store
from app.models.store_settings import StoreSettings
from app.services import store_settings_service


def test_two_simultaneous_first_writes_do_not_collide() -> None:
    engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    setup = SessionLocal()
    try:
        store = Store(name="Loja Concorrência Settings")
        setup.add(store)
        setup.commit()
        setup.refresh(store)
        store_id = store.id
    finally:
        setup.close()

    barrier = threading.Barrier(2)
    results: dict[str, str] = {}

    def attempt_upsert(name: str, updates: dict) -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)  # maximiza a chance dos dois INSERTs colidirem de verdade
            store_settings_service.upsert(session, store_id, updates)
            results[name] = "success"
        except Exception as exc:  # nunca deveria acontecer — é isso que o teste prova
            session.rollback()
            results[name] = f"error: {exc}"
        finally:
            session.close()

    thread_a = threading.Thread(target=attempt_upsert, args=("A", {"max_assignees_per_task": 1}))
    thread_b = threading.Thread(target=attempt_upsert, args=("B", {"auto_logout_minutes": 10}))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)

    try:
        # As duas gravações têm que ter sucedido — nenhuma colisão, nenhum erro.
        assert results == {"A": "success", "B": "success"}, results

        verify = SessionLocal()
        try:
            final_settings = verify.get(StoreSettings, store_id)
            assert final_settings is not None
            assert final_settings.max_assignees_per_task in (1, None)
            assert final_settings.auto_logout_minutes in (5, 10)
        finally:
            verify.close()
    finally:
        cleanup = SessionLocal()
        try:
            cleanup.execute(text("DELETE FROM store_settings WHERE store_id = :store_id"), {"store_id": store_id})
            cleanup.execute(text("DELETE FROM stores WHERE id = :store_id"), {"store_id": store_id})
            cleanup.commit()
        finally:
            cleanup.close()
