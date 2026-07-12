from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StatusFaktury, TypDokumentu


class Faktura(Base):
    __tablename__ = "faktury"

    id: Mapped[int] = mapped_column(primary_key=True)

    numer: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    typ_dokumentu: Mapped[TypDokumentu] = mapped_column(
        Enum(TypDokumentu, name="typ_dokumentu"),
        nullable=False,
        default=TypDokumentu.FAKTURA_VAT,
    )

    klient_id: Mapped[int] = mapped_column(ForeignKey("klienci.id"), nullable=False)

    data_wystawienia: Mapped[date] = mapped_column(Date, nullable=False)
    data_sprzedazy: Mapped[date] = mapped_column(Date, nullable=False)
    termin_platnosci: Mapped[date] = mapped_column(Date, nullable=False)

    waluta: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    kurs_waluty: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("1")
    )

    status: Mapped[StatusFaktury] = mapped_column(
        Enum(StatusFaktury, name="status_faktury"),
        nullable=False,
        default=StatusFaktury.ROBOCZA,
    )

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    klient: Mapped["Klient"] = relationship(back_populates="faktury")
    pozycje: Mapped[list["PozycjaFaktury"]] = relationship(
        back_populates="faktura", cascade="all, delete-orphan"
    )

    @property
    def suma_netto_grosze(self) -> int:
        return sum(pozycja.wartosc_netto_grosze for pozycja in self.pozycje)

    @property
    def suma_vat_grosze(self) -> int:
        return sum(pozycja.wartosc_vat_grosze for pozycja in self.pozycje)

    @property
    def suma_brutto_grosze(self) -> int:
        return sum(pozycja.wartosc_brutto_grosze for pozycja in self.pozycje)
