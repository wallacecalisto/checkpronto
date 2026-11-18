from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Texto (não ENUM nativo do Postgres), mesmo motivo de USER_ROLES/TASK_TYPES:
# mudar os valores aceitos no futuro é só uma migration no CHECK.
AUDIT_ACTOR_TYPES = ("USER", "EMPLOYEE")
AUDIT_ACTIONS = (
    "CREATE",
    "UPDATE",
    "ACTIVATE",
    "DEACTIVATE",
    "START",
    "COMPLETE",
    "VALIDATE",
    "DELETE",
    "RESET_PIN",
    "RESET_PASSWORD",
)


class AuditLog(Base):

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(f"actor_type IN {AUDIT_ACTOR_TYPES}", name="ck_audit_logs_actor_type_valid"),
        CheckConstraint(f"action IN {AUDIT_ACTIONS}", name="ck_audit_logs_action_valid"),
        CheckConstraint(
            "(actor_type = 'USER' AND actor_user_id IS NOT NULL AND actor_employee_id IS NULL) OR "
            "(actor_type = 'EMPLOYEE' AND actor_employee_id IS NOT NULL AND actor_user_id IS NULL)",
            name="ck_audit_logs_actor_matches_type",
        ),
        Index("ix_audit_logs_store_created", "store_id", "created_at"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nulo só reservado para uma eventual ação verdadeiramente global (nenhuma
    # ainda) — todas as ações auditadas hoje pertencem a uma loja.
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), index=True)

    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    actor_employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"))
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)

    action: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int] = mapped_column(nullable=False)

    before_data: Mapped[dict | None] = mapped_column(JSONB)
    after_data: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    store: Mapped["Store | None"] = relationship()  # noqa: F821
