"""faktury_faza25_rentownosc

Revision ID: 6017974908ed
Revises: 86bc323db850
Create Date: 2026-07-19 21:19:18.747439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6017974908ed'
down_revision: Union[str, Sequence[str], None] = '86bc323db850'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('produkty', sa.Column('koszt_zakupu_grosze', sa.BigInteger(), nullable=True))

    op.create_table(
        'koszty_reczne',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('firma_id', sa.Integer(), nullable=False),
        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('kwota_grosze', sa.BigInteger(), nullable=False),
        sa.Column('kategoria', sa.String(length=100), nullable=False),
        sa.Column('opis', sa.String(length=1000), nullable=True),
        sa.Column('utworzono', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('zaktualizowano', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firma_id'], ['firmy.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('koszty_reczne')
    op.drop_column('produkty', 'koszt_zakupu_grosze')
