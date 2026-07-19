"""faktury_faza21_split_payment_mpp

Revision ID: 65371e481704
Revises: b470b3bc5c69
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65371e481704'
down_revision: Union[str, Sequence[str], None] = 'b470b3bc5c69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default do backfillu istniejacych wierszy (kolumny NOT NULL na
    # tabelach, ktore moga juz miec dane) - usuwany zaraz po, docelowo wartosc
    # domyslna zyje tylko po stronie modelu (Python-level default), jak przy
    # analogicznej kolumnie boolowskiej dodanej w Fazie 8 (tryb_blokady_ujemnego_stanu).
    op.add_column(
        'produkty',
        sa.Column('objety_zalacznikiem_15', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.alter_column('produkty', 'objety_zalacznikiem_15', server_default=None)

    op.add_column(
        'faktury',
        sa.Column('wymaga_mpp', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.alter_column('faktury', 'wymaga_mpp', server_default=None)

    op.add_column(
        'firmy',
        sa.Column('bank_numer_konta_vat', sa.String(length=34), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('firmy', 'bank_numer_konta_vat')
    op.drop_column('faktury', 'wymaga_mpp')
    op.drop_column('produkty', 'objety_zalacznikiem_15')
