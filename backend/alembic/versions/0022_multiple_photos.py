
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5b8c1f3a9d4'
down_revision: Union[str, Sequence[str], None] = 'd4a7f2c6e8b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for table in ("task_assignments", "task_execution_history", "checklist_execution_items"):
        op.add_column(
            table,
            sa.Column(
                'extra_photo_urls',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ("checklist_execution_items", "task_execution_history", "task_assignments"):
        op.drop_column(table, 'extra_photo_urls')
