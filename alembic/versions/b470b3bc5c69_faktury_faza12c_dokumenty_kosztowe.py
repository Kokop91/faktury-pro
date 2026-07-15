"""faktury_faza12c_dokumenty_kosztowe

Revision ID: b470b3bc5c69
Revises: 268b0e6a8c00
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b470b3bc5c69'
down_revision: Union[str, Sequence[str], None] = '268b0e6a8c00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # UWAGA: nie tworzymy typu osobnym Enum(...).create(checkfirst=True) przed
    # create_table - SQLAlchemy 2.0's Table.create() i tak probuje utworzyc
    # enum uzyty w kolumnie przy KAZDYM wywolaniu create_table niezaleznie od
    # create_type=False (sprawdzone empirycznie - to nie sledzi tego flagi dla
    # pojedynczych Table.create(), tylko dla metadata.create_all()), wiec
    # podwojna proba konczy sie bledem "already exists". Typ ma powstac
    # WYLACZNIE tutaj, przy tworzeniu tabeli.
    status_dokumentu_kosztowego_kolumna = sa.Enum(
        'NOWA', 'ZAAKCEPTOWANA', 'DO_WYJASNIENIA', name='status_dokumentu_kosztowego'
    )

    op.create_table(
        'dokumenty_kosztowe',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('firma_id', sa.Integer(), nullable=False),
        sa.Column('kontrahent_nazwa', sa.String(length=512), nullable=True),
        sa.Column('kontrahent_nip', sa.String(length=20), nullable=True),
        sa.Column('numer_faktury', sa.String(length=256), nullable=False),
        sa.Column('numer_ksef', sa.String(length=37), nullable=False),
        sa.Column('data_wystawienia', sa.Date(), nullable=False),
        sa.Column('data_trwalego_zapisu', sa.DateTime(timezone=True), nullable=False),
        sa.Column('waluta', sa.String(length=3), nullable=False),
        sa.Column('netto_grosze', sa.BigInteger(), nullable=False),
        sa.Column('brutto_grosze', sa.BigInteger(), nullable=False),
        sa.Column('vat_grosze_pln', sa.BigInteger(), nullable=False),
        sa.Column('xml_oryginalny', sa.Text(), nullable=False),
        sa.Column('status', status_dokumentu_kosztowego_kolumna, nullable=False, server_default='NOWA'),
        sa.Column('pobrano_o', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('zaktualizowano', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firma_id'], ['firmy.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numer_ksef'),
    )
    op.create_index(
        op.f('ix_dokumenty_kosztowe_numer_ksef'), 'dokumenty_kosztowe', ['numer_ksef'], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_dokumenty_kosztowe_numer_ksef'), table_name='dokumenty_kosztowe')
    op.drop_table('dokumenty_kosztowe')

    sa.Enum(name='status_dokumentu_kosztowego').drop(op.get_bind(), checkfirst=True)
