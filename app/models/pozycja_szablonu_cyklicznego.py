from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StawkaVat


class PozycjaSzablonuCyklicznego(Base):
    """Analogicznie do PozycjaFaktury, ale BEZ wyliczonych wartosc_netto/vat/brutto -
    to tylko szablon (cena/ilosc/stawka); przeliczenie na grosze dzieje sie
    dopiero przy faktycznym wygenerowaniu faktury (app/services/faktury.py -
    ten sam kod co przy recznym tworzeniu faktury, patrz faktury_cykliczne.py)."""

    __tablename__ = "pozycje_szablonu_cyklicznego"

    id: Mapped[int] = mapped_column(primary_key=True)
    szablon_id: Mapped[int] = mapped_column(
        ForeignKey("szablony_cykliczne.id"), nullable=False
    )

    nazwa: Mapped[str] = mapped_column(String(500), nullable=False)
    ilosc: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    jednostka_miary: Mapped[str] = mapped_column(String(20), nullable=False)

    cena_netto_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stawka_vat: Mapped[StawkaVat] = mapped_column(
        Enum(StawkaVat, name="stawka_vat"), nullable=False
    )

    szablon: Mapped["SzablonCykliczny"] = relationship(back_populates="pozycje")
