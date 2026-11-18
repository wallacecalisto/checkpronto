from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Employee(Base):

    __tablename__ = "employees"
    __table_args__ = (
        Index("ix_employees_store_active", "store_id", "active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role_title: Mapped[str | None] = mapped_column(String(80))

    # PIN: hash de 4 dígitos, nunca texto puro. Nulo até o gestor definir um PIN.
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    pin_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    pin_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Exclusão lógica: nunca apagar um funcionário que já tem histórico associado.
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    store: Mapped["Store"] = relationship(back_populates="employees")  # noqa: F821
    sector: Mapped["Sector"] = relationship(back_populates="employees")  # noqa: F821
