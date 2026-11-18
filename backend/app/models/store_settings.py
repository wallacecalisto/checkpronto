from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StoreSettings(Base):

    __tablename__ = "store_settings"

    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)
    max_assignees_per_task: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operational_checklists_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    auto_logout_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    hide_task_timer: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    require_live_photo_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    require_pin_on_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    enable_audio_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    shifts: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    store: Mapped["Store"] = relationship(back_populates="store_settings")  # noqa: F821
