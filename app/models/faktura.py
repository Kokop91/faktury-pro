from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StatusFaktury, StatusKsef, TypDokumentu


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

    # Odniesienie do innego dokumentu: dla FAKTURA_KORYGUJACA/NOTA_KORYGUJACA to dokument
    # pierwotny ktory jest korygowany; dla FAKTURA_KONCOWA to rozliczana faktura zaliczkowa.
    dokument_powiazany_id: Mapped[int | None] = mapped_column(
        ForeignKey("faktury.id", name="fk_faktury_dokument_powiazany_id_faktury"),
        nullable=True,
    )
    przyczyna_korekty: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Faza 15 - wypelnione wylacznie dla faktur powstalych automatycznie z
    # szablonu cyklicznego. okres_cykliczny to termin (okres) ktory ta faktura
    # rozlicza - trzymany OSOBNO od data_wystawienia, bo ta ostatnia jest
    # edytowalna dopoki faktura jest robocza, a okres musi zostac niezmienny
    # (uzywany do wykrywania, ktore terminy szablonu sa juz pokryte).
    szablon_cykliczny_id: Mapped[int | None] = mapped_column(
        ForeignKey("szablony_cykliczne.id"), nullable=True
    )
    okres_cykliczny: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Faza 12B - stan wysylki do KSeF, niezalezny od `status` biznesowego
    # powyzej. numer_ksef i upo_xml sa wypelniane dopiero po przyjeciu przez
    # KSeF; przyczyna_odrzucenia_ksef - po odrzuceniu. ksef_numer_ref_sesji/
    # _faktury trzymane, zeby dalo sie sprawdzic/dokonczyc status wysylki bez
    # ponownego wysylania calego dokumentu (patrz app/services/ksef_service.py).
    status_ksef: Mapped[StatusKsef] = mapped_column(
        Enum(StatusKsef, name="status_ksef"),
        nullable=False,
        default=StatusKsef.NIE_WYSLANA,
    )
    numer_ksef: Mapped[str | None] = mapped_column(String(37), nullable=True)
    upo_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    przyczyna_odrzucenia_ksef: Mapped[str | None] = mapped_column(Text, nullable=True)
    ksef_numer_ref_sesji: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ksef_numer_ref_faktury: Mapped[str | None] = mapped_column(String(36), nullable=True)

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    klient: Mapped["Klient"] = relationship(back_populates="faktury")
    pozycje: Mapped[list["PozycjaFaktury"]] = relationship(
        back_populates="faktura", cascade="all, delete-orphan"
    )
    platnosci: Mapped[list["PlatnoscFaktury"]] = relationship(
        back_populates="faktura", cascade="all, delete-orphan"
    )

    dokument_powiazany: Mapped["Faktura | None"] = relationship(
        remote_side=[id],
        foreign_keys=[dokument_powiazany_id],
        back_populates="korekty_i_rozliczenia",
    )
    korekty_i_rozliczenia: Mapped[list["Faktura"]] = relationship(
        back_populates="dokument_powiazany"
    )

    szablon_cykliczny: Mapped["SzablonCykliczny | None"] = relationship(
        back_populates="faktury_wygenerowane"
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

    @property
    def suma_wplat_grosze(self) -> int:
        return sum(platnosc.kwota_grosze for platnosc in self.platnosci)

    @property
    def kwota_pozostala_grosze(self) -> int:
        return max(self.suma_brutto_grosze - self.suma_wplat_grosze, 0)
