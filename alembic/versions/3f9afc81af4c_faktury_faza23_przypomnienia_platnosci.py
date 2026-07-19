"""faktury_faza23_przypomnienia_platnosci

Revision ID: 3f9afc81af4c
Revises: 65371e481704
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f9afc81af4c'
down_revision: Union[str, Sequence[str], None] = '65371e481704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('firmy', sa.Column('przypomnienia_dni_przed', sa.Integer(), nullable=True))
    op.add_column(
        'firmy',
        sa.Column('przypomnienia_w_dniu_terminu', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.alter_column('firmy', 'przypomnienia_w_dniu_terminu', server_default=None)
    op.add_column('firmy', sa.Column('przypomnienia_dni_po', sa.Integer(), nullable=True))
    op.add_column('firmy', sa.Column('przypomnienia_szablon_temat', sa.String(length=255), nullable=True))
    op.add_column('firmy', sa.Column('przypomnienia_szablon_tresc', sa.Text(), nullable=True))

    typ_przypomnienia_kolumna = sa.Enum(
        'PRZED_TERMINEM', 'W_DNIU_TERMINU', 'PO_TERMINIE', name='typ_przypomnienia'
    )
    op.create_table(
        'przypomnienia_platnosci',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('faktura_id', sa.Integer(), nullable=False),
        sa.Column('typ', typ_przypomnienia_kolumna, nullable=False),
        sa.Column('adres_email', sa.String(length=255), nullable=False),
        sa.Column('wyslano_o', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['faktura_id'], ['faktury.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('faktura_id', 'typ', name='uq_przypomnienie_faktura_typ'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('przypomnienia_platnosci')
    sa.Enum(name='typ_przypomnienia').drop(op.get_bind(), checkfirst=True)

    op.drop_column('firmy', 'przypomnienia_szablon_tresc')
    op.drop_column('firmy', 'przypomnienia_szablon_temat')
    op.drop_column('firmy', 'przypomnienia_dni_po')
    op.drop_column('firmy', 'przypomnienia_w_dniu_terminu')
    op.drop_column('firmy', 'przypomnienia_dni_przed')
