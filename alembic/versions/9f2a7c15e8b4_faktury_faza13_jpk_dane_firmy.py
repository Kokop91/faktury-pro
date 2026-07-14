"""faktury_faza13_jpk_dane_firmy

Revision ID: 9f2a7c15e8b4
Revises: 4b1e6c7a9d23
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f2a7c15e8b4'
down_revision: Union[str, Sequence[str], None] = '4b1e6c7a9d23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    typ_podatnika_enum = sa.Enum('OSOBA_FIZYCZNA', 'OSOBA_NIEFIZYCZNA', name='typ_podatnika')
    typ_podatnika_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'firmy',
        sa.Column(
            'typ_podatnika', typ_podatnika_enum, nullable=False,
            server_default='OSOBA_NIEFIZYCZNA',
        ),
    )
    op.add_column('firmy', sa.Column('imie_pierwsze', sa.String(length=30), nullable=True))
    op.add_column('firmy', sa.Column('nazwisko', sa.String(length=81), nullable=True))
    op.add_column('firmy', sa.Column('data_urodzenia', sa.Date(), nullable=True))
    op.add_column('firmy', sa.Column('kod_urzedu_skarbowego', sa.String(length=4), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('firmy', 'kod_urzedu_skarbowego')
    op.drop_column('firmy', 'data_urodzenia')
    op.drop_column('firmy', 'nazwisko')
    op.drop_column('firmy', 'imie_pierwsze')
    op.drop_column('firmy', 'typ_podatnika')

    sa.Enum(name='typ_podatnika').drop(op.get_bind(), checkfirst=True)
