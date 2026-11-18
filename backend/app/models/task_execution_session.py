import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaskExecutionSession(Base):

    __tablename__ = "task_execution_sessions"
    __table_args__ = (
        Index("ix_task_execution_sessions_task_assignment_id", "task_assignment_id"),
        Index("ix_task_execution_sessions_employee_id", "employee_id"),
        Index("ix_task_execution_sessions_store_id", "store_id"),
        Index(
            "ux_task_execution_sessions_open_employee",
            "employee_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("task_assignments.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    leave_reason: Mapped[str | None] = mapped_column(String(500))
    execution_group_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), index=True)
