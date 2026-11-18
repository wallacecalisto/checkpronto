from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Store(Base):
    """Uma loja/unidade da operação. Base do isolamento multi-tenant do sistema."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="store")  # noqa: F821
    employees: Mapped[list["Employee"]] = relationship(back_populates="store")  # noqa: F821
    sectors: Mapped[list["Sector"]] = relationship(back_populates="store")  # noqa: F821
    store_settings: Mapped["StoreSettings | None"] = relationship(  # noqa: F821
        back_populates="store", uselist=False, cascade="all, delete-orphan"
    )
