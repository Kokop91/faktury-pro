from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StatusOferty


class Oferta(Base):
    """Oferta (wycena) poprzedzajaca fakture (Faza 24) - NIE jest dokumentem
    ksiegowym i nie podlega KSeF/JPK (patrz app/services/jpk_service.py,
    app/services/ksef_service.py - zadne z nich nie odwoluja sie do tego
    modelu). Klient akceptuje/odrzuca oferte recznie, poza appka; dopiero
    zaakceptowana oferta moze zostac przeksztalcona w fakture robocza
    (app/services/oferty.py:wystaw_fakture_z_oferty)."""

    __tablename__ = "oferty"

    id: Mapped[int] = mapped_column(primary_key=True)

    numer: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    klient_id: Mapped[int] = mapped_column(ForeignKey("klienci.id"), nullable=False)

    data_wystawienia: Mapped[date] = mapped_column(Date, nullable=False)
    data_waznosci: Mapped[date] = mapped_column(Date, nullable=False)

    waluta: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    kurs_waluty: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("1")
    )

    status: Mapped[StatusOferty] = mapped_column(
        Enum(StatusOferty, name="status_oferty"),
        nullable=False,
        default=StatusOferty.ROBOCZA,
    )

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    klient: Mapped["Klient"] = relationship(back_populates="oferty")
    pozycje: Mapped[list["PozycjaOferty"]] = relationship(
        back_populates="oferta", cascade="all, delete-orphan"
    )
    faktury_wygenerowane: Mapped[list["Faktura"]] = relationship(
        back_populates="oferta_zrodlowa"
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
