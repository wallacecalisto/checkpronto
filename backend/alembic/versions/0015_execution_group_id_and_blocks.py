from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# revision identifiers, used by Alembic.
revision: str = 'e4a8b2f6c9d1'
down_revision: Union[str, Sequence[str], None] = 'd2f7a9c1e5b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # --- 1. task_execution_history.execution_group_id -----------------------------
    op.add_column(
        'task_execution_history', sa.Column('execution_group_id', PG_UUID(as_uuid=True), nullable=True)
    )
    history_ids = conn.execute(sa.text('SELECT id FROM task_execution_history ORDER BY id')).scalars().all()
    for history_id in history_ids:
        conn.execute(
            sa.text('UPDATE task_execution_history SET execution_group_id = gen_random_uuid() WHERE id = :id'),
            {'id': history_id},
        )
    op.alter_column('task_execution_history', 'execution_group_id', nullable=False)
    op.create_index(
        'ix_task_execution_history_execution_group_id', 'task_execution_history', ['execution_group_id']
    )

    # --- 2. task_execution_sessions.execution_group_id -----------------------------
    op.add_column(
        'task_execution_sessions', sa.Column('execution_group_id', PG_UUID(as_uuid=True), nullable=True)
    )
    op.create_index(
        'ix_task_execution_sessions_execution_group_id', 'task_execution_sessions', ['execution_group_id']
    )

    # --- 3. task_execution_blocks ---------------------------------------------------
    op.create_table(
        'task_execution_blocks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'task_assignment_id',
            sa.Integer(),
            sa.ForeignKey('task_assignments.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id', ondelete='RESTRICT'), nullable=False),
        sa.Column(
            'blocked_by_employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='RESTRICT'), nullable=False
        ),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_group_id', PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_index('ix_task_execution_blocks_task_assignment_id', 'task_execution_blocks', ['task_assignment_id'])
    op.create_index('ix_task_execution_blocks_store_id', 'task_execution_blocks', ['store_id'])
    op.create_index('ix_task_execution_blocks_execution_group_id', 'task_execution_blocks', ['execution_group_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_task_execution_blocks_execution_group_id', table_name='task_execution_blocks')
    op.drop_index('ix_task_execution_blocks_store_id', table_name='task_execution_blocks')
    op.drop_index('ix_task_execution_blocks_task_assignment_id', table_name='task_execution_blocks')
    op.drop_table('task_execution_blocks')

    op.drop_index('ix_task_execution_sessions_execution_group_id', table_name='task_execution_sessions')
    op.drop_column('task_execution_sessions', 'execution_group_id')

    op.drop_index('ix_task_execution_history_execution_group_id', table_name='task_execution_history')
    op.drop_column('task_execution_history', 'execution_group_id')
