"""faktury_faza27_status_i_koszt_pz

Revision ID: 86543dc9edab
Revises: 7f5a554bf78f
Create Date: 2026-07-23 00:00:39.609353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86543dc9edab'
down_revision: Union[str, Sequence[str], None] = '7f5a554bf78f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # W odroznieniu od create_table (patrz komentarz w b470b3bc5c69 - tworzy typ
    # enuma automatycznie), add_column tego NIE robi - sprawdzone empirycznie
    # (ALTER TABLE ... ADD COLUMN status status_dokumentu_magazynowego zawiodl na
    # "typ nie istnieje"). Typ trzeba wiec utworzyc jawnie PRZED add_column, a
    # potem przekazac create_type=False, zeby add_column nie probowal utworzyc go
    # ponownie.
    status_dokumentu_magazynowego_typ = sa.Enum(
        'ROBOCZY', 'ZATWIERDZONY', name='status_dokumentu_magazynowego'
    )
    status_dokumentu_magazynowego_typ.create(op.get_bind(), checkfirst=True)

    # server_default='ZATWIERDZONY' (nazwa skladowej enuma, nie .value) - dotyczy
    # WYLACZNIE juz istniejacych wierszy w tej tabeli w momencie migracji. Nowe
    # dokumenty dostaja 'ROBOCZY' jawnie w kodzie (magazyn_service.py), server_default
    # tu jest tylko po to, zeby ALTER TABLE ADD COLUMN nie zawiodl na NOT NULL
    # bez wartosci dla juz istniejacych, dawno rozliczonych dokumentow.
    op.add_column(
        'dokumenty_magazynowe',
        sa.Column(
            'status',
            sa.Enum(
                'ROBOCZY', 'ZATWIERDZONY',
                name='status_dokumentu_magazynowego',
                create_type=False,
            ),
            nullable=False,
            server_default='ZATWIERDZONY',
        ),
    )
    op.add_column(
        'pozycje_dokumentow_magazynowych',
        sa.Column('cena_zakupu_netto_grosze', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('pozycje_dokumentow_magazynowych', 'cena_zakupu_netto_grosze')
    op.drop_column('dokumenty_magazynowe', 'status')
    sa.Enum(name='status_dokumentu_magazynowego').drop(op.get_bind(), checkfirst=True)
