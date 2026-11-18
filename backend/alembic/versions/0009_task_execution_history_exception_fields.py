from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd8f1a3c5e7b9'
down_revision: Union[str, Sequence[str], None] = 'c7a4f0e9b1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('task_execution_history', sa.Column('justification', sa.String(length=1000), nullable=True))
    op.add_column('task_execution_history', sa.Column('observation', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('task_execution_history', 'observation')
    op.drop_column('task_execution_history', 'justification')
