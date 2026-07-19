from datetime import date, datetime

from sqlalchemy import Boolean, Date, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StawkaVat, TrybBlokadyStanu, TypPodatnika


class Firma(Base):
    __tablename__ = "firmy"

    id: Mapped[int] = mapped_column(primary_key=True)

    nazwa: Mapped[str] = mapped_column(String(255), nullable=False)
    nip: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)

    ulica: Mapped[str | None] = mapped_column(String(255))
    kod_pocztowy: Mapped[str | None] = mapped_column(String(10))
    miejscowosc: Mapped[str | None] = mapped_column(String(255))
    kraj: Mapped[str] = mapped_column(String(100), nullable=False, default="Polska")

    email: Mapped[str | None] = mapped_column(String(255))
    telefon: Mapped[str | None] = mapped_column(String(30))

    bank_nazwa: Mapped[str | None] = mapped_column(String(255))
    bank_numer_konta: Mapped[str | None] = mapped_column(String(34))
    # Faza 21 (split payment) - rachunek VAT wyswietlany na fakturach objetych
    # MPP obok zwyklego numeru konta. Czysto informacyjne - appka nie zarzadza
    # samymi przelewami ani nie sprawdza zgodnosci tego numeru z bankiem.
    bank_numer_konta_vat: Mapped[str | None] = mapped_column(String(34))

    logo_path: Mapped[str | None] = mapped_column(String(500))

    # Faza 13 (JPK_V7) - forma prawna firmy okresla ksztalt sekcji Podmiot1:
    # osoba fizyczna (JDG) potrzebuje imie/nazwisko/data urodzenia, osoba
    # niefizyczna (spolka) - samej nazwy (juz w polu "nazwa"). Brak pola REGON -
    # lokalna definicja Podmiot1 w schemacie JPK_V7 nie ma tego pola.
    typ_podatnika: Mapped[TypPodatnika] = mapped_column(
        Enum(TypPodatnika, name="typ_podatnika"),
        nullable=False,
        default=TypPodatnika.OSOBA_NIEFIZYCZNA,
    )
    imie_pierwsze: Mapped[str | None] = mapped_column(String(30))
    nazwisko: Mapped[str | None] = mapped_column(String(81))
    data_urodzenia: Mapped[date | None] = mapped_column(Date)
    kod_urzedu_skarbowego: Mapped[str | None] = mapped_column(String(4))

    domyslna_stawka_vat: Mapped[StawkaVat] = mapped_column(
        Enum(StawkaVat, name="stawka_vat"),
        nullable=False,
        default=StawkaVat.STAWKA_23,
    )

    # Tryb reakcji na proby zejscia ze stanu magazynowego ponizej zera (WZ/RW/MM) -
    # patrz app/services/magazyn_service.py. "ostrzegaj" jako domyslny - mniej
    # frustrujacy na start, do potwierdzenia z uzytkownikiem.
    tryb_blokady_ujemnego_stanu: Mapped[TrybBlokadyStanu] = mapped_column(
        Enum(TrybBlokadyStanu, name="tryb_blokady_stanu"),
        nullable=False,
        default=TrybBlokadyStanu.OSTRZEGAJ,
    )

    # Faza 23 - harmonogram przypomnien o platnosci, kazdy z trzech rodzajow
    # niezaleznie wylaczalny (None/False = wylaczony). Szablon tresci jest
    # opcjonalny - pusty (None) oznacza uzycie wbudowanego domyslnego szablonu
    # (patrz app/services/przypomnienia_service.py), zeby funkcja dzialala od
    # razu bez wymuszania konfiguracji przed pierwszym uzyciem.
    przypomnienia_dni_przed: Mapped[int | None] = mapped_column(Integer)
    przypomnienia_w_dniu_terminu: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    przypomnienia_dni_po: Mapped[int | None] = mapped_column(Integer)
    przypomnienia_szablon_temat: Mapped[str | None] = mapped_column(String(255))
    przypomnienia_szablon_tresc: Mapped[str | None] = mapped_column(Text)

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    klienci: Mapped[list["Klient"]] = relationship(back_populates="firma")
    produkty: Mapped[list["Produkt"]] = relationship(back_populates="firma")
    magazyny: Mapped[list["Magazyn"]] = relationship(back_populates="firma")
    dokumenty_kosztowe: Mapped[list["DokumentKosztowy"]] = relationship(back_populates="firma")
    koszty_reczne: Mapped[list["KosztReczny"]] = relationship(back_populates="firma")
