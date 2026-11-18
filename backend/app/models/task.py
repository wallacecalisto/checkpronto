import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

DAYS_OF_WEEK = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")

TASK_ASSIGNMENT_STATUSES = ("PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED")

TASK_RESULTS = ("FEITO", "NAO_FEITO")


class Task(Base):

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))

    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer)

    requires_photo_proof: Mapped[bool] = mapped_column(nullable=False, server_default="false")

    active: Mapped[bool] = mapped_column(nullable=False, server_default="true")

    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TaskAssignment(Base):

    __tablename__ = "task_assignments"
    __table_args__ = (
        CheckConstraint(f"day_of_week IN {DAYS_OF_WEEK}", name="ck_task_assignments_day_valid"),
        CheckConstraint(f"status IN {TASK_ASSIGNMENT_STATUSES}", name="ck_task_assignments_status_valid"),
        CheckConstraint(f"result IS NULL OR result IN {TASK_RESULTS}", name="ck_task_assignments_result_valid"),
        CheckConstraint(
            "result <> 'NAO_FEITO' OR justification IS NOT NULL",
            name="ck_task_assignments_justification_required",
        ),
        CheckConstraint(
            "status <> 'BLOCKED' OR block_reason IS NOT NULL",
            name="ck_task_assignments_block_reason_required",
        ),
        Index("ix_task_assignments_store_day", "store_id", "day_of_week"),
        Index("ix_task_assignments_store_status", "store_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)

    shift: Mapped[str] = mapped_column(String(50), nullable=False)

    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="PENDING")

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    result: Mapped[str | None] = mapped_column(String(20))
    justification: Mapped[str | None] = mapped_column(String(1000))
    observation: Mapped[str | None] = mapped_column(String(1000))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    extra_photo_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")

    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    block_reason: Mapped[str | None] = mapped_column(String(500))
    blocked_by_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"))

    started_by_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"))
    completed_by_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"))
    started_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    completed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    task: Mapped["Task"] = relationship()
    sector: Mapped["Sector"] = relationship()


class TaskExecutionHistory(Base):

    __tablename__ = "task_execution_history"
    __table_args__ = (
        CheckConstraint(f"result IN {TASK_RESULTS}", name="ck_task_execution_history_result_valid"),
        Index("ix_task_execution_history_store_completed", "store_id", "completed_at"),
        Index("ix_task_execution_history_employee_completed", "employee_id", "completed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False)
    task_title: Mapped[str] = mapped_column(String(160), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)

    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer)

    justification: Mapped[str | None] = mapped_column(String(1000))
    observation: Mapped[str | None] = mapped_column(String(1000))

    photo_url: Mapped[str | None] = mapped_column(String(500))
    extra_photo_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")

    worked_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    execution_group_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Imutável por design (só INSERT, nunca UPDATE/DELETE) — mesmo padrão de
    # audit_logs/checklist_validations: só created_at, sem updated_at.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
