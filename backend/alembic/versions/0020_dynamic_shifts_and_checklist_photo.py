
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b8f1c4e9a3d7'
down_revision: Union[str, Sequence[str], None] = 'c7e2f4b8a1d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'store_settings',
        sa.Column(
            'shifts',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text('\'["Manhã", "Tarde", "Noite"]\'::jsonb'),
        ),
    )
    op.add_column('tasks', sa.Column('shift', sa.String(length=50), nullable=True))
    op.add_column('checklist_templates', sa.Column('shift', sa.String(length=50), nullable=True))
    op.add_column(
        'checklist_template_items', sa.Column('requires_photo', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('checklist_execution_items', sa.Column('photo_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('checklist_execution_items', 'photo_url')
    op.drop_column('checklist_template_items', 'requires_photo')
    op.drop_column('checklist_templates', 'shift')
    op.drop_column('tasks', 'shift')
    op.drop_column('store_settings', 'shifts')
