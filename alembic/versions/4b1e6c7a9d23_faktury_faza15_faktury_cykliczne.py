"""faktury_faza15_faktury_cykliczne

Revision ID: 4b1e6c7a9d23
Revises: 7cc9a1a354fd
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4b1e6c7a9d23'
down_revision: Union[str, Sequence[str], None] = '7cc9a1a354fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'szablony_cykliczne',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('klient_id', sa.Integer(), nullable=False),
        sa.Column(
            'typ_dokumentu',
            postgresql.ENUM(
                'FAKTURA_VAT', 'PROFORMA', 'FAKTURA_ZALICZKOWA', 'FAKTURA_KONCOWA',
                'FAKTURA_KORYGUJACA', 'NOTA_KORYGUJACA', 'RACHUNEK',
                name='typ_dokumentu', create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('waluta', sa.String(length=3), nullable=False),
        sa.Column(
            'czestotliwosc',
            sa.Enum('MIESIECZNA', 'KWARTALNA', 'ROCZNA', name='czestotliwosc_cykliczna'),
            nullable=False,
        ),
        sa.Column('dzien_generowania', sa.Integer(), nullable=False),
        sa.Column('data_poczatku', sa.Date(), nullable=False),
        sa.Column('data_konca', sa.Date(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('AKTYWNY', 'WSTRZYMANY', name='status_szablonu_cyklicznego'),
            nullable=False,
        ),
        sa.Column('utworzono', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('zaktualizowano', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['klient_id'], ['klienci.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_szablony_cykliczne_klient_id'), 'szablony_cykliczne', ['klient_id'], unique=False,
    )

    op.create_table(
        'pozycje_szablonu_cyklicznego',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('szablon_id', sa.Integer(), nullable=False),
        sa.Column('nazwa', sa.String(length=500), nullable=False),
        sa.Column('ilosc', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('jednostka_miary', sa.String(length=20), nullable=False),
        sa.Column('cena_netto_grosze', sa.BigInteger(), nullable=False),
        sa.Column('stawka_vat', postgresql.ENUM('STAWKA_23', 'STAWKA_8', 'STAWKA_5', 'STAWKA_0', 'ZW', name='stawka_vat', create_type=False), nullable=False),
        sa.ForeignKeyConstraint(['szablon_id'], ['szablony_cykliczne.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_pozycje_szablonu_cyklicznego_szablon_id'),
        'pozycje_szablonu_cyklicznego', ['szablon_id'], unique=False,
    )

    op.add_column('faktury', sa.Column('szablon_cykliczny_id', sa.Integer(), nullable=True))
    op.add_column('faktury', sa.Column('okres_cykliczny', sa.Date(), nullable=True))
    op.create_index(
        op.f('ix_faktury_szablon_cykliczny_id'), 'faktury', ['szablon_cykliczny_id'], unique=False,
    )
    op.create_foreign_key(
        'fk_faktury_szablon_cykliczny_id_szablony_cykliczne',
        'faktury', 'szablony_cykliczne', ['szablon_cykliczny_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_faktury_szablon_cykliczny_id_szablony_cykliczne', 'faktury', type_='foreignkey',
    )
    op.drop_index(op.f('ix_faktury_szablon_cykliczny_id'), table_name='faktury')
    op.drop_column('faktury', 'okres_cykliczny')
    op.drop_column('faktury', 'szablon_cykliczny_id')

    op.drop_index(op.f('ix_pozycje_szablonu_cyklicznego_szablon_id'), table_name='pozycje_szablonu_cyklicznego')
    op.drop_table('pozycje_szablonu_cyklicznego')

    op.drop_index(op.f('ix_szablony_cykliczne_klient_id'), table_name='szablony_cykliczne')
    op.drop_table('szablony_cykliczne')

    sa.Enum(name='status_szablonu_cyklicznego').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='czestotliwosc_cykliczna').drop(op.get_bind(), checkfirst=True)
