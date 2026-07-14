from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import CzestotliwoscCykliczna, StatusSzablonuCyklicznego, TypDokumentu


class SzablonCykliczny(Base):
    __tablename__ = "szablony_cykliczne"

    id: Mapped[int] = mapped_column(primary_key=True)
    klient_id: Mapped[int] = mapped_column(ForeignKey("klienci.id"), nullable=False)

    typ_dokumentu: Mapped[TypDokumentu] = mapped_column(
        Enum(TypDokumentu, name="typ_dokumentu"),
        nullable=False,
        default=TypDokumentu.FAKTURA_VAT,
    )
    waluta: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")

    czestotliwosc: Mapped[CzestotliwoscCykliczna] = mapped_column(
        Enum(CzestotliwoscCykliczna, name="czestotliwosc_cykliczna"), nullable=False
    )
    # Dzien miesiaca (1-31) generowania - dla miesiecy krotszych niz ta wartosc
    # (np. 31 w lutym) uzywany jest ostatni dzien danego miesiaca, patrz
    # app/services/faktury_cykliczne.py:_wystap_w_miesiacu.
    dzien_generowania: Mapped[int] = mapped_column(Integer, nullable=False)

    data_poczatku: Mapped[date] = mapped_column(Date, nullable=False)
    data_konca: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[StatusSzablonuCyklicznego] = mapped_column(
        Enum(StatusSzablonuCyklicznego, name="status_szablonu_cyklicznego"),
        nullable=False,
        default=StatusSzablonuCyklicznego.AKTYWNY,
    )

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    klient: Mapped["Klient"] = relationship()
    pozycje: Mapped[list["PozycjaSzablonuCyklicznego"]] = relationship(
        back_populates="szablon", cascade="all, delete-orphan"
    )
    faktury_wygenerowane: Mapped[list["Faktura"]] = relationship(
        back_populates="szablon_cykliczny"
    )
