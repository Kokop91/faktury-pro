"""faktury_faza12b_wysylka_ksef

Revision ID: 268b0e6a8c00
Revises: 9f2a7c15e8b4
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '268b0e6a8c00'
down_revision: Union[str, Sequence[str], None] = '9f2a7c15e8b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    status_ksef_enum = sa.Enum(
        'NIE_WYSLANA', 'WYSYLANIE_W_TOKU', 'PRZYJETA', 'ODRZUCONA', name='status_ksef'
    )
    status_ksef_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'faktury',
        sa.Column(
            'status_ksef', status_ksef_enum, nullable=False,
            server_default='NIE_WYSLANA',
        ),
    )
    op.add_column('faktury', sa.Column('numer_ksef', sa.String(length=37), nullable=True))
    op.add_column('faktury', sa.Column('upo_xml', sa.Text(), nullable=True))
    op.add_column(
        'faktury', sa.Column('przyczyna_odrzucenia_ksef', sa.Text(), nullable=True)
    )
    op.add_column(
        'faktury', sa.Column('ksef_numer_ref_sesji', sa.String(length=36), nullable=True)
    )
    op.add_column(
        'faktury', sa.Column('ksef_numer_ref_faktury', sa.String(length=36), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('faktury', 'ksef_numer_ref_faktury')
    op.drop_column('faktury', 'ksef_numer_ref_sesji')
    op.drop_column('faktury', 'przyczyna_odrzucenia_ksef')
    op.drop_column('faktury', 'upo_xml')
    op.drop_column('faktury', 'numer_ksef')
    op.drop_column('faktury', 'status_ksef')

    sa.Enum(name='status_ksef').drop(op.get_bind(), checkfirst=True)
