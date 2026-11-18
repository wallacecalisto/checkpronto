from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f4b6d0a2c8e1'
down_revision: Union[str, Sequence[str], None] = 'e2a5c9f1b3d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('stores', 'logo_url')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('stores', sa.Column('logo_url', sa.String(length=500), nullable=True))
