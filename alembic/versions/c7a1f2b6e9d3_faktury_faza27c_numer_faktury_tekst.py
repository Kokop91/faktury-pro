"""faktury_faza27c_numer_faktury_tekst

Revision ID: c7a1f2b6e9d3
Revises: 86543dc9edab
Create Date: 2026-07-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a1f2b6e9d3'
down_revision: Union[str, Sequence[str], None] = '86543dc9edab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'dokumenty_magazynowe',
        sa.Column('numer_faktury_tekst', sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('dokumenty_magazynowe', 'numer_faktury_tekst')
