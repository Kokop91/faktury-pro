from datetime import date, datetime

from sqlalchemy import BigInteger, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class KosztReczny(Base):
    """Recznie wprowadzony koszt spoza KSeF (Faza 25) - wydatki gotowkowe/
    niefakturowane, ktorych appka nigdy nie zobaczy przez integracje z KSeF
    (Faza 12C). Prosty rejestr: kwota wpisywana wprost przez uzytkownika, bez
    rozbicia na netto/VAT (w odroznieniu od DokumentKosztowy) - to nie jest
    faktura zakupowa, tylko zapis "wydalem X zl na Y"."""

    __tablename__ = "koszty_reczne"

    id: Mapped[int] = mapped_column(primary_key=True)
    firma_id: Mapped[int] = mapped_column(ForeignKey("firmy.id"), nullable=False)

    data: Mapped[date] = mapped_column(Date, nullable=False)
    kwota_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kategoria: Mapped[str] = mapped_column(String(100), nullable=False)
    opis: Mapped[str | None] = mapped_column(String(1000))

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    firma: Mapped["Firma"] = relationship(back_populates="koszty_reczne")
