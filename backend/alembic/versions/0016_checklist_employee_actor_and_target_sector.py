from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3c7d9a2b6e4'
down_revision: Union[str, Sequence[str], None] = 'e4a8b2f6c9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'checklist_executions',
        sa.Column(
            'executed_by_employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='RESTRICT'), nullable=True
        ),
    )
    op.alter_column('checklist_executions', 'executed_by_user_id', nullable=True)
    op.create_check_constraint(
        'ck_checklist_executions_actor_xor',
        'checklist_executions',
        "(executed_by_employee_id IS NOT NULL AND executed_by_user_id IS NULL) OR "
        "(executed_by_employee_id IS NULL AND executed_by_user_id IS NOT NULL)",
    )

    op.add_column(
        'checklist_templates',
        sa.Column('target_sector_id', sa.Integer(), sa.ForeignKey('sectors.id', ondelete='RESTRICT'), nullable=True),
    )
    op.create_index('ix_checklist_templates_target_sector_id', 'checklist_templates', ['target_sector_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_checklist_templates_target_sector_id', table_name='checklist_templates')
    op.drop_column('checklist_templates', 'target_sector_id')

    op.drop_constraint('ck_checklist_executions_actor_xor', 'checklist_executions', type_='check')
    op.alter_column('checklist_executions', 'executed_by_user_id', nullable=False)
    op.drop_column('checklist_executions', 'executed_by_employee_id')
