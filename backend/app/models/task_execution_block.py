import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaskExecutionBlock(Base):

    __tablename__ = "task_execution_blocks"
    __table_args__ = (
        Index("ix_task_execution_blocks_task_assignment_id", "task_assignment_id"),
        Index("ix_task_execution_blocks_store_id", "store_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("task_assignments.id", ondelete="RESTRICT"), nullable=False
    )
    # Denormalizado — mesmo padrão de isolamento direto usado em toda tabela
    # "filha" do projeto.
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)
    blocked_by_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    execution_group_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), index=True)
