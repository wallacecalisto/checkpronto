from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7a4f0e9b1d2'
down_revision: Union[str, Sequence[str], None] = 'e33ec633771f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TASK_RESULTS = ('FEITO', 'NAO_FEITO')


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tasks', sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True))

    op.create_table(
        'task_execution_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('task_title', sa.String(length=160), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('result', sa.String(length=20), nullable=False),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(f"result IN {_TASK_RESULTS}", name='ck_task_execution_history_result_valid'),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_task_execution_history_store_completed', 'task_execution_history', ['store_id', 'completed_at']
    )
    op.create_index(
        'ix_task_execution_history_employee_completed', 'task_execution_history', ['employee_id', 'completed_at']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_task_execution_history_employee_completed', table_name='task_execution_history')
    op.drop_index('ix_task_execution_history_store_completed', table_name='task_execution_history')
    op.drop_table('task_execution_history')
    op.drop_column('tasks', 'estimated_duration_minutes')
