"""faktury_faza24_oferty

Revision ID: 86bc323db850
Revises: 3f9afc81af4c
Create Date: 2026-07-19 20:46:21.024255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '86bc323db850'
down_revision: Union[str, Sequence[str], None] = '3f9afc81af4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'liczniki_numeracji_ofert',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rok', sa.Integer(), nullable=False),
        sa.Column('ostatni_numer', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rok', name='uq_liczniki_numeracji_ofert_rok'),
    )

    op.create_table(
        'oferty',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numer', sa.String(length=100), nullable=False),
        sa.Column('klient_id', sa.Integer(), nullable=False),
        sa.Column('data_wystawienia', sa.Date(), nullable=False),
        sa.Column('data_waznosci', sa.Date(), nullable=False),
        sa.Column('waluta', sa.String(length=3), nullable=False),
        sa.Column('kurs_waluty', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ROBOCZA', 'WYSLANA', 'ZAAKCEPTOWANA', 'ODRZUCONA', 'WYGASLA', name='status_oferty'),
            nullable=False,
        ),
        sa.Column('utworzono', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('zaktualizowano', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['klient_id'], ['klienci.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_oferty_numer'), 'oferty', ['numer'], unique=False)

    op.create_table(
        'pozycje_ofert',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('oferta_id', sa.Integer(), nullable=False),
        sa.Column('nazwa', sa.String(length=500), nullable=False),
        sa.Column('ilosc', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('jednostka_miary', sa.String(length=20), nullable=False),
        sa.Column('cena_netto_grosze', sa.BigInteger(), nullable=False),
        sa.Column(
            'stawka_vat',
            postgresql.ENUM('STAWKA_23', 'STAWKA_8', 'STAWKA_5', 'STAWKA_0', 'ZW', name='stawka_vat', create_type=False),
            nullable=False,
        ),
        sa.Column('wartosc_netto_grosze', sa.BigInteger(), nullable=False),
        sa.Column('wartosc_vat_grosze', sa.BigInteger(), nullable=False),
        sa.Column('wartosc_brutto_grosze', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['oferta_id'], ['oferty.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('faktury', sa.Column('oferta_zrodlowa_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_faktury_oferta_zrodlowa_id'), 'faktury', ['oferta_zrodlowa_id'], unique=False,
    )
    op.create_foreign_key(
        'fk_faktury_oferta_zrodlowa_id_oferty',
        'faktury', 'oferty', ['oferta_zrodlowa_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_faktury_oferta_zrodlowa_id_oferty', 'faktury', type_='foreignkey')
    op.drop_index(op.f('ix_faktury_oferta_zrodlowa_id'), table_name='faktury')
    op.drop_column('faktury', 'oferta_zrodlowa_id')

    op.drop_table('pozycje_ofert')

    op.drop_index(op.f('ix_oferty_numer'), table_name='oferty')
    op.drop_table('oferty')

    op.drop_table('liczniki_numeracji_ofert')

    sa.Enum(name='status_oferty').drop(op.get_bind(), checkfirst=True)
