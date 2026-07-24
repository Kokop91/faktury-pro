from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura
from app.models.enums import StatusFaktury, StatusKsef
from app.schemas.dashboard import (
    DashboardOut,
    KafelkiDashboarduOut,
    PunktWykresuPrzychodowOut,
)
from app.services import dokumenty_kosztowe_service, raporty_service, rentownosc_service
from app.services.platnosci import lista_naleznosci, oblicz_status_efektywny, zbuduj_fakture_out

# Faktury robocze nie zostaly jeszcze "wystawione" w sensie biznesowym, a anulowane
# nie licza sie do przychodu - obie kategorie sa wylaczone z kafelkow i wykresu.
STATUSY_WYLACZONE_Z_PRZYCHODU = frozenset({StatusFaktury.ROBOCZA, StatusFaktury.ANULOWANA})
LICZBA_MIESIECY_WYKRESU = 12


def _pierwszy_dzien_miesiaca(d: date) -> date:
    return d.replace(day=1)


def _przesun_miesiace(d: date, delta: int) -> date:
    indeks = d.year * 12 + (d.month - 1) + delta
    return date(indeks // 12, indeks % 12 + 1, 1)


def pobierz_dashboard(db: Session, dzisiaj: date | None = None) -> DashboardOut:
    dzisiaj = dzisiaj or date.today()
    poczatek_biezacego_miesiaca = _pierwszy_dzien_miesiaca(dzisiaj)
    poczatek_okna_wykresu = _przesun_miesiace(
        poczatek_biezacego_miesiaca, -(LICZBA_MIESIECY_WYKRESU - 1)
    )

    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje))
        .where(
            Faktura.status.notin_(STATUSY_WYLACZONE_Z_PRZYCHODU),
            Faktura.data_wystawienia >= poczatek_okna_wykresu,
        )
    )
    faktury_okna = list(db.execute(zapytanie).scalars().unique().all())

    # Kubelki wykresu inicjowane zerami z gory, zeby miesiace bez zadnej faktury
    # tez byly widoczne na osi (a nie po prostu pominiete w serii danych).
    kubelki: dict[tuple[int, int], int] = {}
    kursor = poczatek_okna_wykresu
    for _ in range(LICZBA_MIESIECY_WYKRESU):
        kubelki[(kursor.year, kursor.month)] = 0
        kursor = _przesun_miesiace(kursor, 1)

    przychod_biezacy_miesiac_grosze = 0
    liczba_faktur_biezacy_miesiac = 0

    for faktura in faktury_okna:
        klucz = (faktura.data_wystawienia.year, faktura.data_wystawienia.month)
        if klucz in kubelki:
            kubelki[klucz] += faktura.suma_brutto_grosze
        if faktura.data_wystawienia >= poczatek_biezacego_miesiaca:
            przychod_biezacy_miesiac_grosze += faktura.suma_brutto_grosze
            liczba_faktur_biezacy_miesiac += 1

    wykres = [
        PunktWykresuPrzychodowOut(rok=rok, miesiac=miesiac, suma_brutto_grosze=suma)
        for (rok, miesiac), suma in sorted(kubelki.items())
    ]

    faktury_naleznosci, suma_naleznosci_grosze = lista_naleznosci(db, dzisiaj)
    faktury_po_terminie = sorted(
        (
            f
            for f in faktury_naleznosci
            if oblicz_status_efektywny(f, dzisiaj) == StatusFaktury.PO_TERMINIE
        ),
        key=lambda f: f.termin_platnosci,
    )
    kwota_po_terminie_grosze = sum(f.kwota_pozostala_grosze for f in faktury_po_terminie)

    # Faza 12D - podsumowanie integracji KSeF. Robocze/anulowane celowo
    # wylaczone z "oczekujacych" (mirror STATUSY_WYLACZONE_Z_PRZYCHODU powyzej) -
    # nigdy nie maja byc wysylane, wiec nie sa czyms na co appka "czeka".
    liczba_faktur_oczekujacych_ksef = db.execute(
        select(func.count())
        .select_from(Faktura)
        .where(
            Faktura.status.notin_(STATUSY_WYLACZONE_Z_PRZYCHODU),
            Faktura.status_ksef == StatusKsef.NIE_WYSLANA,
        )
    ).scalar_one()

    zapytanie_odrzucone = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje))
        .where(Faktura.status_ksef == StatusKsef.ODRZUCONA)
        .order_by(Faktura.zaktualizowano.desc())
    )
    faktury_odrzucone_ksef = list(db.execute(zapytanie_odrzucone).scalars().unique().all())

    liczba_dokumentow_kosztowych_nowych = dokumenty_kosztowe_service.liczba_nowych(db)

    # Faza 25 - marza biezacego miesiaca i wykres przychody/koszty, ta sama
    # "zero konfiguracji" filozofia co reszta dashboardu.
    _poczatek_miesiaca, _koniec_miesiaca = rentownosc_service.zakres_dat(
        dzisiaj.year, dzisiaj.month, "miesieczny"
    )
    marza_biezacy_miesiac = rentownosc_service.marza_okresu(
        db, _poczatek_miesiaca, _koniec_miesiaca
    )
    # faktury_okna to JUZ dokladnie ten sam 12-miesieczny zakres/filtr statusu,
    # ktorego wykres_przychody_koszty by inaczej zapytal ponownie - podanie go
    # tutaj oszczedza drugie zapytanie + hydratacje ORM (zmierzone jako ~30%
    # calego czasu ladowania dashboardu przy wiekszej ilosci faktur).
    wykres_przychodow_kosztow = rentownosc_service.wykres_przychody_koszty(
        db, dzisiaj, faktury=faktury_okna
    )

    kafelki = KafelkiDashboarduOut(
        przychod_biezacy_miesiac_grosze=przychod_biezacy_miesiac_grosze,
        liczba_faktur_biezacy_miesiac=liczba_faktur_biezacy_miesiac,
        naleznosci_grosze=suma_naleznosci_grosze,
        liczba_faktur_po_terminie=len(faktury_po_terminie),
        kwota_po_terminie_grosze=kwota_po_terminie_grosze,
        liczba_faktur_oczekujacych_ksef=liczba_faktur_oczekujacych_ksef,
        liczba_faktur_odrzuconych_ksef=len(faktury_odrzucone_ksef),
        liczba_dokumentow_kosztowych_nowych=liczba_dokumentow_kosztowych_nowych,
    )

    return DashboardOut(
        kafelki=kafelki,
        wykres_przychodow=wykres,
        faktury_po_terminie=[zbuduj_fakture_out(f, dzisiaj) for f in faktury_po_terminie],
        faktury_odrzucone_ksef=[zbuduj_fakture_out(f, dzisiaj) for f in faktury_odrzucone_ksef],
        ponizej_minimum=raporty_service.lista_ponizej_minimum(db, magazyn_id=None),
        marza_biezacy_miesiac=marza_biezacy_miesiac,
        wykres_przychodow_kosztow=wykres_przychodow_kosztow,
    )
