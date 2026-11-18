from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd2f7a9c1e5b3'
down_revision: Union[str, Sequence[str], None] = 'c1e6f3a8d4b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('task_assignments', sa.Column('blocked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('task_assignments', sa.Column('block_reason', sa.String(length=500), nullable=True))
    op.add_column(
        'task_assignments',
        sa.Column(
            'blocked_by_employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='RESTRICT'), nullable=True
        ),
    )

    op.drop_constraint('ck_task_assignments_status_valid', 'task_assignments', type_='check')
    op.create_check_constraint(
        'ck_task_assignments_status_valid',
        'task_assignments',
        "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED')",
    )
    op.create_check_constraint(
        'ck_task_assignments_block_reason_required',
        'task_assignments',
        "status <> 'BLOCKED' OR block_reason IS NOT NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_task_assignments_block_reason_required', 'task_assignments', type_='check')
    op.drop_constraint('ck_task_assignments_status_valid', 'task_assignments', type_='check')
    op.create_check_constraint(
        'ck_task_assignments_status_valid',
        'task_assignments',
        "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED')",
    )

    op.drop_column('task_assignments', 'blocked_by_employee_id')
    op.drop_column('task_assignments', 'block_reason')
    op.drop_column('task_assignments', 'blocked_at')
