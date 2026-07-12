from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import StawkaVat


class PozycjaFaktury(Base):
    __tablename__ = "pozycje_faktury"

    id: Mapped[int] = mapped_column(primary_key=True)
    faktura_id: Mapped[int] = mapped_column(ForeignKey("faktury.id"), nullable=False)

    nazwa: Mapped[str] = mapped_column(String(500), nullable=False)
    ilosc: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    jednostka_miary: Mapped[str] = mapped_column(String(20), nullable=False)

    cena_netto_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stawka_vat: Mapped[StawkaVat] = mapped_column(
        Enum(StawkaVat, name="stawka_vat"), nullable=False
    )

    wartosc_netto_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wartosc_vat_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wartosc_brutto_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)

    faktura: Mapped["Faktura"] = relationship(back_populates="pozycje")
