
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4a7f2c6e8b1'
down_revision: Union[str, Sequence[str], None] = 'b8f1c4e9a3d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE tasks SET shift = 'Geral' WHERE shift IS NULL")
    op.execute("UPDATE checklist_templates SET shift = 'Geral' WHERE shift IS NULL")
    op.alter_column('tasks', 'shift', existing_type=sa.String(length=50), nullable=False)
    op.alter_column('checklist_templates', 'shift', existing_type=sa.String(length=50), nullable=False)
    op.alter_column(
        'store_settings',
        'shifts',
        server_default=sa.text('\'["Geral"]\'::jsonb'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'store_settings',
        'shifts',
        server_default=sa.text('\'["Manhã", "Tarde", "Noite"]\'::jsonb'),
    )
    op.alter_column('checklist_templates', 'shift', existing_type=sa.String(length=50), nullable=True)
    op.alter_column('tasks', 'shift', existing_type=sa.String(length=50), nullable=True)
