"""faktury_faza14_weryfikacja_bialej_listy

Revision ID: 7cc9a1a354fd
Revises: 16304fc92992
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cc9a1a354fd'
down_revision: Union[str, Sequence[str], None] = '16304fc92992'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'weryfikacje_bialej_listy',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('klient_id', sa.Integer(), nullable=True),
        sa.Column('faktura_id', sa.Integer(), nullable=True),
        sa.Column('nip', sa.String(length=10), nullable=False),
        sa.Column('numer_konta', sa.String(length=34), nullable=True),
        sa.Column('data_na_dzien', sa.Date(), nullable=False),
        sa.Column('znaleziono', sa.Boolean(), nullable=False),
        sa.Column('status_vat', sa.String(length=50), nullable=True),
        sa.Column('nazwa_podmiotu', sa.String(length=255), nullable=True),
        sa.Column('konto_zgodne', sa.Boolean(), nullable=True),
        sa.Column('sprawdzono_o', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['klient_id'], ['klienci.id'], ),
        sa.ForeignKeyConstraint(['faktura_id'], ['faktury.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_weryfikacje_bialej_listy_klient_id'),
        'weryfikacje_bialej_listy', ['klient_id'], unique=False,
    )
    op.create_index(
        op.f('ix_weryfikacje_bialej_listy_faktura_id'),
        'weryfikacje_bialej_listy', ['faktura_id'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_weryfikacje_bialej_listy_faktura_id'), table_name='weryfikacje_bialej_listy')
    op.drop_index(op.f('ix_weryfikacje_bialej_listy_klient_id'), table_name='weryfikacje_bialej_listy')
    op.drop_table('weryfikacje_bialej_listy')
