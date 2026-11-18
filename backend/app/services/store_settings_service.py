
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.store_settings import StoreSettings

DEFAULT_MAX_ASSIGNEES_PER_TASK: int | None = None  # ilimitado
DEFAULT_OPERATIONAL_CHECKLISTS_ENABLED = True
DEFAULT_AUTO_LOGOUT_MINUTES = 5
DEFAULT_HIDE_TASK_TIMER = False
DEFAULT_REQUIRE_LIVE_PHOTO_ONLY = False
DEFAULT_REQUIRE_PIN_ON_COMPLETE = False
DEFAULT_ENABLE_AUDIO_ALERTS = False
DEFAULT_SHIFTS = ["Geral"]


def _defaults() -> dict[str, object]:
    return {
        "max_assignees_per_task": DEFAULT_MAX_ASSIGNEES_PER_TASK,
        "operational_checklists_enabled": DEFAULT_OPERATIONAL_CHECKLISTS_ENABLED,
        "auto_logout_minutes": DEFAULT_AUTO_LOGOUT_MINUTES,
        "hide_task_timer": DEFAULT_HIDE_TASK_TIMER,
        "require_live_photo_only": DEFAULT_REQUIRE_LIVE_PHOTO_ONLY,
        "require_pin_on_complete": DEFAULT_REQUIRE_PIN_ON_COMPLETE,
        "enable_audio_alerts": DEFAULT_ENABLE_AUDIO_ALERTS,
        "shifts": list(DEFAULT_SHIFTS),
    }


def get_effective_settings(db: Session, store_id: int) -> StoreSettings:
    settings = db.get(StoreSettings, store_id)
    if settings is not None:
        return settings
    return StoreSettings(store_id=store_id, **_defaults())


def upsert(db: Session, store_id: int, updates: dict) -> StoreSettings:
    values = {**_defaults(), **updates, "store_id": store_id}
    stmt = pg_insert(StoreSettings).values(**values)

    update_columns = {field: stmt.excluded[field] for field in updates} if updates else None
    if update_columns:
        stmt = stmt.on_conflict_do_update(index_elements=[StoreSettings.store_id], set_=update_columns)
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=[StoreSettings.store_id])

    db.execute(stmt)
    db.commit()
    return db.get(StoreSettings, store_id)
