from datetime import date, datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StatusDokumentuKosztowego


class DokumentKosztowy(Base):
    """Faktura zakupowa (kosztowa) pobrana z KSeF - wystawiona przez
    kontrahenta na NIP naszej firmy (Faza 12C). Czysto rejestrowy/podglądowy:
    appka NIE generuje z niej żadnych zapisów księgowych ani zmian stanu
    magazynowego - to potencjalny temat na przyszłość."""

    __tablename__ = "dokumenty_kosztowe"

    id: Mapped[int] = mapped_column(primary_key=True)
    firma_id: Mapped[int] = mapped_column(ForeignKey("firmy.id"), nullable=False)

    kontrahent_nazwa: Mapped[str | None] = mapped_column(String(512))
    kontrahent_nip: Mapped[str | None] = mapped_column(String(20))

    numer_faktury: Mapped[str] = mapped_column(String(256), nullable=False)
    numer_ksef: Mapped[str] = mapped_column(String(37), nullable=False, unique=True, index=True)

    data_wystawienia: Mapped[date] = mapped_column(nullable=False)
    # Data trwalego zapisu w repozytorium KSeF (permanentStorageDate) - NIE
    # data wystawienia/przyjecia. Sluzy jako punkt startowy kolejnego
    # sprawdzenia (patrz app/services/ksef_koszty_service.py) - MF
    # rekomenduje wylacznie ten typ daty do przyrostowego pobierania, bo jest
    # odporny na asynchroniczne opoznienia przetwarzania po stronie KSeF.
    data_trwalego_zapisu: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    waluta: Mapped[str] = mapped_column(String(3), nullable=False)
    netto_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    brutto_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # KSeF zawsze zwraca vatAmount przeliczony na PLN (niezaleznie od waluty
    # faktury) - stad odrebna nazwa pola, zeby nie sugerowac falszywie, ze to
    # kwota w `waluta` tak jak netto/brutto powyzej.
    vat_grosze_pln: Mapped[int] = mapped_column(BigInteger, nullable=False)

    xml_oryginalny: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[StatusDokumentuKosztowego] = mapped_column(
        Enum(StatusDokumentuKosztowego, name="status_dokumentu_kosztowego"),
        nullable=False,
        default=StatusDokumentuKosztowego.NOWA,
    )

    pobrano_o: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    firma: Mapped["Firma"] = relationship(back_populates="dokumenty_kosztowe")
