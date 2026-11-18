
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7e2f4b8a1d9'
down_revision: Union[str, Sequence[str], None] = 'b3f8a2d5c1e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('store_settings', sa.Column('auto_logout_minutes', sa.Integer(), nullable=False, server_default='5'))
    op.add_column(
        'store_settings', sa.Column('hide_task_timer', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'store_settings',
        sa.Column('require_live_photo_only', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'store_settings',
        sa.Column('require_pin_on_complete', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'store_settings', sa.Column('enable_audio_alerts', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('store_settings', 'enable_audio_alerts')
    op.drop_column('store_settings', 'require_pin_on_complete')
    op.drop_column('store_settings', 'require_live_photo_only')
    op.drop_column('store_settings', 'hide_task_timer')
    op.drop_column('store_settings', 'auto_logout_minutes')
