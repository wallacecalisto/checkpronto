from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e33ec633771f'
down_revision: Union[str, Sequence[str], None] = 'fe1d7ba83468'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_AUDIT_ACTIONS = ('CREATE', 'UPDATE', 'ACTIVATE', 'DEACTIVATE', 'START', 'COMPLETE', 'VALIDATE')
_NEW_AUDIT_ACTIONS = _OLD_AUDIT_ACTIONS + ('DELETE', 'RESET_PIN', 'RESET_PASSWORD')


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users', sa.Column('must_change_password', sa.Boolean(), server_default='false', nullable=False)
    )

    # Apaga execuções de checklist antigas iniciadas via PIN (e tudo que
    # depende delas) antes de remover a coluna que as identifica como tal.
    op.execute(
        "DELETE FROM checklist_validations WHERE checklist_execution_item_id IN ("
        "  SELECT id FROM checklist_execution_items WHERE checklist_execution_id IN ("
        "    SELECT id FROM checklist_executions WHERE executed_by_employee_id IS NOT NULL"
        "  )"
        ")"
    )
    op.execute(
        "DELETE FROM checklist_execution_items WHERE checklist_execution_id IN ("
        "  SELECT id FROM checklist_executions WHERE executed_by_employee_id IS NOT NULL"
        ")"
    )
    op.execute("DELETE FROM checklist_executions WHERE executed_by_employee_id IS NOT NULL")

    op.drop_column('checklist_executions', 'executed_by_employee_id')
    op.alter_column('checklist_executions', 'executed_by_user_id', existing_type=sa.Integer(), nullable=False)

    # Derruba junto ck_tasks_type_valid.
    op.drop_column('tasks', 'type')

    # Derruba junto ck_task_assignments_type_valid e
    # ck_task_assignments_actor_matches_type (as duas referenciam `type`).
    op.drop_column('task_assignments', 'type')

    op.drop_constraint('ck_audit_logs_action_valid', 'audit_logs', type_='check')
    op.create_check_constraint('ck_audit_logs_action_valid', 'audit_logs', f"action IN {_NEW_AUDIT_ACTIONS}")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_audit_logs_action_valid', 'audit_logs', type_='check')
    op.create_check_constraint('ck_audit_logs_action_valid', 'audit_logs', f"action IN {_OLD_AUDIT_ACTIONS}")

    op.add_column('task_assignments', sa.Column('type', sa.String(length=20), nullable=True))
    op.execute("UPDATE task_assignments SET type = 'OPERACIONAL'")
    op.alter_column('task_assignments', 'type', existing_type=sa.String(length=20), nullable=False)
    op.create_check_constraint('ck_task_assignments_type_valid', 'task_assignments', "type IN ('OPERACIONAL', 'GESTAO')")
    op.create_check_constraint(
        'ck_task_assignments_actor_matches_type',
        'task_assignments',
        "(type = 'OPERACIONAL' AND started_by_user_id IS NULL AND completed_by_user_id IS NULL) OR "
        "(type = 'GESTAO' AND started_by_employee_id IS NULL AND completed_by_employee_id IS NULL "
        "AND assigned_employee_id IS NULL)",
    )

    op.add_column('tasks', sa.Column('type', sa.String(length=20), nullable=True))
    op.execute("UPDATE tasks SET type = 'OPERACIONAL'")
    op.alter_column('tasks', 'type', existing_type=sa.String(length=20), nullable=False)
    op.create_check_constraint('ck_tasks_type_valid', 'tasks', "type IN ('OPERACIONAL', 'GESTAO')")

    # Dados apagados no upgrade() não voltam — isto só restaura o SCHEMA.
    op.alter_column('checklist_executions', 'executed_by_user_id', existing_type=sa.Integer(), nullable=True)
    op.add_column('checklist_executions', sa.Column('executed_by_employee_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'checklist_executions_executed_by_employee_id_fkey',
        'checklist_executions',
        'employees',
        ['executed_by_employee_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_check_constraint(
        'ck_checklist_executions_actor_xor',
        'checklist_executions',
        "(executed_by_employee_id IS NOT NULL AND executed_by_user_id IS NULL) OR "
        "(executed_by_employee_id IS NULL AND executed_by_user_id IS NOT NULL)",
    )

    op.drop_column('users', 'must_change_password')
