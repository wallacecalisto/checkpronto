from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1e6f3a8d4b2'
down_revision: Union[str, Sequence[str], None] = 'b7d4a1f9c2e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # --- 1. task_assignments.assigned_employee_id -> sector_id ------------------
    op.add_column(
        'task_assignments',
        sa.Column('sector_id', sa.Integer(), sa.ForeignKey('sectors.id', ondelete='RESTRICT'), nullable=True),
    )

    # Caso A: agendamento tinha um funcionário atribuído -> herda o setor DELE.
    conn.execute(
        sa.text(
            """
            UPDATE task_assignments
            SET sector_id = employees.sector_id
            FROM employees
            WHERE task_assignments.assigned_employee_id = employees.id
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE task_assignments
            SET sector_id = (
                SELECT sectors.id FROM sectors
                WHERE sectors.store_id = task_assignments.store_id
                ORDER BY sectors.id
                LIMIT 1
            )
            WHERE task_assignments.sector_id IS NULL
            """
        )
    )

    op.alter_column('task_assignments', 'sector_id', nullable=False)
    op.create_index('ix_task_assignments_sector_id', 'task_assignments', ['sector_id'])
    op.drop_column('task_assignments', 'assigned_employee_id')

    # --- 2. task_execution_sessions ----------------------------------------------
    op.create_table(
        'task_execution_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'task_assignment_id',
            sa.Integer(),
            sa.ForeignKey('task_assignments.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        # Motivo opcional de uma saída VOLUNTÁRIA (endpoint /leave) — nulo
        # quando a sessão fecha por conclusão da tarefa ou reset semanal.
        sa.Column('leave_reason', sa.String(length=500), nullable=True),
    )
    op.create_index(
        'ix_task_execution_sessions_task_assignment_id', 'task_execution_sessions', ['task_assignment_id']
    )
    op.create_index('ix_task_execution_sessions_employee_id', 'task_execution_sessions', ['employee_id'])
    op.create_index('ix_task_execution_sessions_store_id', 'task_execution_sessions', ['store_id'])
    op.create_index(
        'ux_task_execution_sessions_open_employee',
        'task_execution_sessions',
        ['employee_id'],
        unique=True,
        postgresql_where=sa.text('ended_at IS NULL'),
    )

    # --- 3. task_execution_history.worked_duration_seconds -----------------------
    op.add_column(
        'task_execution_history', sa.Column('worked_duration_seconds', sa.Integer(), nullable=True)
    )
    conn.execute(
        sa.text(
            """
            UPDATE task_execution_history
            SET worked_duration_seconds = GREATEST(
                0, EXTRACT(EPOCH FROM (completed_at - started_at))::integer
            )
            """
        )
    )
    op.alter_column('task_execution_history', 'worked_duration_seconds', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('task_execution_history', 'worked_duration_seconds')

    op.drop_index('ux_task_execution_sessions_open_employee', table_name='task_execution_sessions')
    op.drop_index('ix_task_execution_sessions_store_id', table_name='task_execution_sessions')
    op.drop_index('ix_task_execution_sessions_employee_id', table_name='task_execution_sessions')
    op.drop_index('ix_task_execution_sessions_task_assignment_id', table_name='task_execution_sessions')
    op.drop_table('task_execution_sessions')

    op.add_column(
        'task_assignments',
        sa.Column('assigned_employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='RESTRICT'), nullable=True),
    )
    op.drop_index('ix_task_assignments_sector_id', table_name='task_assignments')
    op.drop_column('task_assignments', 'sector_id')
