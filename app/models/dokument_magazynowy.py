from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StatusDokumentuMagazynowego, TypDokumentuMagazynowego


class DokumentMagazynowy(Base):
    __tablename__ = "dokumenty_magazynowe"

    id: Mapped[int] = mapped_column(primary_key=True)

    typ: Mapped[TypDokumentuMagazynowego] = mapped_column(
        Enum(TypDokumentuMagazynowego, name="typ_dokumentu_magazynowego"),
        nullable=False,
    )
    # Domyslnie ZATWIERDZONY na poziomie bazy (server_default) - dotyczy
    # WYLACZNIE wierszy sprzed tej kolumny (migracja), zeby juz istniejace,
    # rozliczone dokumenty NIE stary sie nagle "edytowalne" po aktualizacji
    # appki. Nowe dokumenty dostaja ROBOCZY jawnie w kodzie serwisu
    # (app/services/magazyn_service.py:utworz_dokument_magazynowy).
    status: Mapped[StatusDokumentuMagazynowego] = mapped_column(
        Enum(StatusDokumentuMagazynowego, name="status_dokumentu_magazynowego"),
        nullable=False,
        # UWAGA: sqlalchemy.Enum domyslnie przechowuje NAZWE skladowej enuma
        # (np. "ZATWIERDZONY"), nie jej .value ("zatwierdzony") - zweryfikowane
        # wprost w istniejacych migracjach (np. status_inwentaryzacji: 'W_TRAKCIE',
        # nie 'w_trakcie'). server_default musi wiec uzyc .name, inaczej Postgres
        # odrzuci go jako nieprawidlowa etykiete enuma.
        server_default=StatusDokumentuMagazynowego.ZATWIERDZONY.name,
    )
    numer: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    data_dokumentu: Mapped[date] = mapped_column(Date, nullable=False)

    # Ktory magazyn/magazyny bierze udzial w dokumencie zalezy od typu (PZ/PW: tylko
    # docelowy, WZ/RW: tylko zrodlowy, MM: oba) - to sprawdzi walidacja w Fazie 8,
    # nie schemat bazy, dlatego oba pola sa tu nullable.
    magazyn_zrodlowy_id: Mapped[int | None] = mapped_column(
        ForeignKey("magazyny.id"), nullable=True
    )
    magazyn_docelowy_id: Mapped[int | None] = mapped_column(
        ForeignKey("magazyny.id"), nullable=True
    )

    # Wylacznie informacyjne powiazanie z faktura (Model B, patrz CLAUDE.md) - zadna
    # logika w tej fazie nie synchronizuje automatycznie dokumentu z faktura.
    faktura_powiazana_id: Mapped[int | None] = mapped_column(
        ForeignKey("faktury.id"), nullable=True
    )

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    magazyn_zrodlowy: Mapped["Magazyn | None"] = relationship(
        foreign_keys=[magazyn_zrodlowy_id]
    )
    magazyn_docelowy: Mapped["Magazyn | None"] = relationship(
        foreign_keys=[magazyn_docelowy_id]
    )
    faktura_powiazana: Mapped["Faktura | None"] = relationship(
        foreign_keys=[faktura_powiazana_id]
    )
    pozycje: Mapped[list["PozycjaDokumentuMagazynowego"]] = relationship(
        back_populates="dokument", cascade="all, delete-orphan"
    )
