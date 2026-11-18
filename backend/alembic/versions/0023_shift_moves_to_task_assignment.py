
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f6c9d2a4b7e1'
down_revision: Union[str, Sequence[str], None] = 'e5b8c1f3a9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('task_assignments', sa.Column('shift', sa.String(length=50), nullable=True))
    op.execute(
        """
        UPDATE task_assignments
        SET shift = tasks.shift
        FROM tasks
        WHERE tasks.id = task_assignments.task_id
        """
    )
    op.alter_column('task_assignments', 'shift', existing_type=sa.String(length=50), nullable=False)
    op.drop_column('tasks', 'shift')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('tasks', sa.Column('shift', sa.String(length=50), nullable=True))
    op.execute(
        """
        UPDATE tasks
        SET shift = (
            SELECT ta.shift FROM task_assignments ta
            WHERE ta.task_id = tasks.id
            ORDER BY ta.id
            LIMIT 1
        )
        """
    )
    op.execute("UPDATE tasks SET shift = 'Geral' WHERE shift IS NULL")
    op.alter_column('tasks', 'shift', existing_type=sa.String(length=50), nullable=False)
    op.drop_column('task_assignments', 'shift')
