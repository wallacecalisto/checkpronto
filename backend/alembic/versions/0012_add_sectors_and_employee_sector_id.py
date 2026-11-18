from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d4a1f9c2e6'
down_revision: Union[str, Sequence[str], None] = 'f4b6d0a2c8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'sectors',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_sectors_store_id', 'sectors', ['store_id'])

    # Nullable por enquanto — vira NOT NULL só depois do backfill abaixo.
    op.add_column(
        'employees',
        sa.Column('sector_id', sa.Integer(), sa.ForeignKey('sectors.id', ondelete='RESTRICT'), nullable=True),
    )

    # --- Backfill: 1 setor "Geral" por loja + mover todo mundo pra lá -----------
    conn = op.get_bind()

    store_ids = conn.execute(sa.text('SELECT id FROM stores ORDER BY id')).scalars().all()
    for store_id in store_ids:
        sector_id = conn.execute(
            sa.text("INSERT INTO sectors (store_id, name) VALUES (:store_id, 'Geral') RETURNING id"),
            {'store_id': store_id},
        ).scalar_one()
        conn.execute(
            sa.text('UPDATE employees SET sector_id = :sector_id WHERE store_id = :store_id'),
            {'sector_id': sector_id, 'store_id': store_id},
        )

    op.alter_column('employees', 'sector_id', nullable=False)
    op.create_index('ix_employees_sector_id', 'employees', ['sector_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_employees_sector_id', table_name='employees')
    op.drop_column('employees', 'sector_id')
    op.drop_index('ix_sectors_store_id', table_name='sectors')
    op.drop_table('sectors')
