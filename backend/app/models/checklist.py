from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

CHECKLIST_SHIFTS = ("MANHA", "TARDE", "NOITE")

CHECKLIST_EXECUTION_STATUSES = ("IN_PROGRESS", "COMPLETED")

CHECKLIST_ITEM_RESPONSES = ("OK", "DIVERGENTE")

CHECKLIST_VALIDATION_RESULTS = ("APROVADO", "DIVERGENTE")


class ChecklistTemplate(Base):

    __tablename__ = "checklist_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)

    target_sector_id: Mapped[int | None] = mapped_column(ForeignKey("sectors.id", ondelete="RESTRICT"))

    shift: Mapped[str] = mapped_column(String(50), nullable=False)

    active: Mapped[bool] = mapped_column(nullable=False, server_default="true")

    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["ChecklistTemplateItem"]] = relationship(
        back_populates="template", order_by="ChecklistTemplateItem.order_index"
    )


class ChecklistTemplateItem(Base):

    __tablename__ = "checklist_template_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_templates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    order_index: Mapped[int] = mapped_column(nullable=False, server_default="0")
    required: Mapped[bool] = mapped_column(nullable=False, server_default="true")

    requires_photo: Mapped[bool] = mapped_column(nullable=False, server_default="false")

    active: Mapped[bool] = mapped_column(nullable=False, server_default="true")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    template: Mapped["ChecklistTemplate"] = relationship(back_populates="items")


class ChecklistExecution(Base):

    __tablename__ = "checklist_executions"
    __table_args__ = (
        CheckConstraint(f"shift IN {CHECKLIST_SHIFTS}", name="ck_checklist_executions_shift_valid"),
        CheckConstraint(f"status IN {CHECKLIST_EXECUTION_STATUSES}", name="ck_checklist_executions_status_valid"),
        CheckConstraint(
            "(executed_by_employee_id IS NOT NULL AND executed_by_user_id IS NULL) OR "
            "(executed_by_employee_id IS NULL AND executed_by_user_id IS NOT NULL)",
            name="ck_checklist_executions_actor_xor",
        ),
        Index("ix_checklist_executions_store_status", "store_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_templates.id", ondelete="RESTRICT"), nullable=False
    )
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)
    shift: Mapped[str] = mapped_column(String(20), nullable=False)

    executed_by_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"))
    executed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="IN_PROGRESS")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    template: Mapped["ChecklistTemplate"] = relationship()
    items: Mapped[list["ChecklistExecutionItem"]] = relationship(back_populates="execution")


class ChecklistExecutionItem(Base):

    __tablename__ = "checklist_execution_items"
    __table_args__ = (
        CheckConstraint(
            f"response IS NULL OR response IN {CHECKLIST_ITEM_RESPONSES}",
            name="ck_checklist_execution_items_response_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    checklist_execution_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_executions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    template_item_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_template_items.id", ondelete="RESTRICT"), nullable=False
    )
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)

    item_description_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)

    # Nulo até o turno responder este item específico — a execução como um
    # todo pode estar IN_PROGRESS com alguns itens ainda sem resposta.
    response: Mapped[str | None] = mapped_column(String(20))
    observation: Mapped[str | None] = mapped_column(String(1000))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    extra_photo_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    execution: Mapped["ChecklistExecution"] = relationship(back_populates="items")
    template_item: Mapped["ChecklistTemplateItem"] = relationship()
    validation: Mapped["ChecklistValidation | None"] = relationship(back_populates="execution_item", uselist=False)


class ChecklistValidation(Base):

    __tablename__ = "checklist_validations"
    __table_args__ = (
        CheckConstraint(f"result IN {CHECKLIST_VALIDATION_RESULTS}", name="ck_checklist_validations_result_valid"),
        CheckConstraint(
            "result <> 'DIVERGENTE' OR justification IS NOT NULL",
            name="ck_checklist_validations_justification_required",
        ),
        UniqueConstraint("checklist_execution_item_id", name="uq_checklist_validations_execution_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    checklist_execution_item_id: Mapped[int] = mapped_column(
        ForeignKey("checklist_execution_items.id", ondelete="RESTRICT"), nullable=False
    )
    # Denormalizado — mesmo motivo de sempre: checagem de tenant direta nesta
    # linha, sem subir duas relações (item -> execução -> loja) só pra isso.
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False)

    validated_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    result: Mapped[str] = mapped_column(String(20), nullable=False)
    justification: Mapped[str | None] = mapped_column(String(1000))

    original_response_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)

    execution_item: Mapped["ChecklistExecutionItem"] = relationship(back_populates="validation")
