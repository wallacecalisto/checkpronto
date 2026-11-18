from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a9d5e1c4f7b8'
down_revision: Union[str, Sequence[str], None] = 'f3c7d9a2b6e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'tasks', sa.Column('requires_photo_proof', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('task_assignments', sa.Column('photo_url', sa.String(length=500), nullable=True))
    op.add_column('task_execution_history', sa.Column('photo_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('task_execution_history', 'photo_url')
    op.drop_column('task_assignments', 'photo_url')
    op.drop_column('tasks', 'requires_photo_proof')
