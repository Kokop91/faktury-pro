import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura, Klient, PozycjaSzablonuCyklicznego, SzablonCykliczny
from app.models.enums import CzestotliwoscCykliczna, StatusSzablonuCyklicznego
from app.schemas.faktura import FakturaCreate, PozycjaFakturyCreate
from app.schemas.szablon_cykliczny import (
    SzablonCyklicznyCreate,
    SzablonCyklicznyOut,
    SzablonCyklicznyUpdate,
    ZaleglaFakturaCykliczna,
    _zwaliduj_ksztalt_szablonu,
)
from app.services import faktury as faktury_service
from app.services import nbp_service

# Ile miesiecy dodac za kazdym "krokiem" wystapienia, wg czestotliwosci.
KROK_MIESIECY: dict[CzestotliwoscCykliczna, int] = {
    CzestotliwoscCykliczna.MIESIECZNA: 1,
    CzestotliwoscCykliczna.KWARTALNA: 3,
    CzestotliwoscCykliczna.ROCZNA: 12,
}

# Horyzont "w przod" (dni) przy szukaniu najblizszego NIEWYGENEROWANEGO terminu
# do wyswietlenia na liscie szablonow (np. gdy szablon nie ma zaleglosci, chcemy
# pokazac najblizszy przyszly termin, nie tylko zalegle). 370 dni z zapasem
# pokrywa nawet czestotliwosc roczna.
HORYZONT_NASTEPNEGO_TERMINU_DNI = 370


def _zaokraglij_do_grosza(wartosc: Decimal) -> int:
    return int(wartosc.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _ostatni_dzien_miesiaca(rok: int, miesiac: int) -> int:
    return calendar.monthrange(rok, miesiac)[1]


def _wystap_w_miesiacu(rok: int, miesiac: int, dzien_generowania: int) -> date:
    """Dzien generowania przyciety do ostatniego dnia danego miesiaca - obsluguje
    np. dzien_generowania=31 w lutym (wystapi 28 albo 29 lutego)."""
    dzien = min(dzien_generowania, _ostatni_dzien_miesiaca(rok, miesiac))
    return date(rok, miesiac, dzien)


def _rok_miesiac_po_krokach(punkt_startowy: date, liczba_krokow: int, krok_miesiecy: int) -> tuple[int, int]:
    indeks_miesiaca = punkt_startowy.year * 12 + (punkt_startowy.month - 1) + liczba_krokow * krok_miesiecy
    return indeks_miesiaca // 12, indeks_miesiaca % 12 + 1


def wygeneruj_terminy(szablon: SzablonCykliczny, do_dnia: date) -> list[date]:
    """Wszystkie terminy (okresy) szablonu od data_poczatku do min(do_dnia,
    data_konca) wlacznie, niezaleznie od tego, czy faktura juz powstala -
    filtrowanie "co jeszcze nie wygenerowane" robi znajdz_zalegle/
    nastepny_niewygenerowany_termin, ta funkcja tylko liczy KALENDARZ."""
    krok_miesiecy = KROK_MIESIECY[szablon.czestotliwosc]
    granica = min(do_dnia, szablon.data_konca) if szablon.data_konca else do_dnia
    if granica < szablon.data_poczatku:
        return []

    terminy: list[date] = []
    i = 0
    while True:
        rok, miesiac = _rok_miesiac_po_krokach(szablon.data_poczatku, i, krok_miesiecy)
        termin = _wystap_w_miesiacu(rok, miesiac, szablon.dzien_generowania)
        if termin > granica:
            break
        if termin >= szablon.data_poczatku:
            terminy.append(termin)
        i += 1
    return terminy


def _juz_wygenerowane_terminy(db: Session, szablon_id: int) -> set[date]:
    return set(
        db.execute(
            select(Faktura.okres_cykliczny).where(
                Faktura.szablon_cykliczny_id == szablon_id,
                Faktura.okres_cykliczny.is_not(None),
            )
        ).scalars().all()
    )


def _oszacuj_sume_brutto_grosze(pozycje: list) -> int:
    suma = 0
    for pozycja in pozycje:
        netto = _zaokraglij_do_grosza(Decimal(pozycja.cena_netto_grosze) * pozycja.ilosc)
        udzial_vat = faktury_service.UDZIAL_STAWKI_VAT[pozycja.stawka_vat]
        vat = _zaokraglij_do_grosza(Decimal(netto) * udzial_vat)
        suma += netto + vat
    return suma


def nastepny_niewygenerowany_termin(db: Session, szablon: SzablonCykliczny) -> date | None:
    if szablon.status != StatusSzablonuCyklicznego.AKTYWNY:
        return None
    horyzont = date.today() + timedelta(days=HORYZONT_NASTEPNEGO_TERMINU_DNI)
    terminy = wygeneruj_terminy(szablon, horyzont)
    if not terminy:
        return None
    wygenerowane = _juz_wygenerowane_terminy(db, szablon.id)
    for termin in terminy:
        if termin not in wygenerowane:
            return termin
    return None


def zbuduj_szablon_out(db: Session, szablon: SzablonCykliczny) -> SzablonCyklicznyOut:
    # Atrybuty przejsciowe (nie mapowane kolumny) - bezpieczne do ustawienia na
    # instancji ORM, tak samo jak status_efektywny w platnosci.zbuduj_fakture_out.
    szablon.suma_brutto_szacowana_grosze = _oszacuj_sume_brutto_grosze(szablon.pozycje)
    szablon.nastepny_termin = nastepny_niewygenerowany_termin(db, szablon)
    return SzablonCyklicznyOut.model_validate(szablon)


def _pobierz_klienta_lub_404(db: Session, klient_id: int) -> Klient:
    klient = db.get(Klient, klient_id)
    if klient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono klienta o podanym id.",
        )
    return klient


def pobierz_szablon(db: Session, szablon_id: int) -> SzablonCykliczny:
    zapytanie = (
        select(SzablonCykliczny)
        .options(selectinload(SzablonCykliczny.pozycje))
        .where(SzablonCykliczny.id == szablon_id)
    )
    szablon = db.execute(zapytanie).scalar_one_or_none()
    if szablon is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono szablonu cyklicznego o podanym id.",
        )
    return szablon


def lista_szablonow(db: Session, tylko_aktywne: bool = False) -> list[SzablonCykliczny]:
    zapytanie = select(SzablonCykliczny).options(selectinload(SzablonCykliczny.pozycje))
    if tylko_aktywne:
        zapytanie = zapytanie.where(SzablonCykliczny.status == StatusSzablonuCyklicznego.AKTYWNY)
    zapytanie = zapytanie.order_by(SzablonCykliczny.id.desc())
    return list(db.execute(zapytanie).scalars().unique().all())


def utworz_szablon(db: Session, dane: SzablonCyklicznyCreate) -> SzablonCykliczny:
    klient = _pobierz_klienta_lub_404(db, dane.klient_id)
    szablon = SzablonCykliczny(
        klient_id=klient.id,
        typ_dokumentu=dane.typ_dokumentu,
        waluta=dane.waluta or klient.domyslna_waluta,
        czestotliwosc=dane.czestotliwosc,
        dzien_generowania=dane.dzien_generowania,
        data_poczatku=dane.data_poczatku,
        data_konca=dane.data_konca,
        pozycje=[
            PozycjaSzablonuCyklicznego(
                nazwa=p.nazwa,
                ilosc=p.ilosc,
                jednostka_miary=p.jednostka_miary,
                cena_netto_grosze=p.cena_netto_grosze,
                stawka_vat=p.stawka_vat,
            )
            for p in dane.pozycje
        ],
    )
    db.add(szablon)
    db.commit()
    db.refresh(szablon)
    return szablon


def aktualizuj_szablon(
    db: Session, szablon_id: int, dane: SzablonCyklicznyUpdate
) -> SzablonCykliczny:
    szablon = pobierz_szablon(db, szablon_id)

    zmiany = dane.model_dump(exclude_unset=True, exclude={"pozycje"})
    if "klient_id" in zmiany:
        _pobierz_klienta_lub_404(db, zmiany["klient_id"])

    typ_docelowy = zmiany.get("typ_dokumentu", szablon.typ_dokumentu)
    pozycje_docelowe = dane.pozycje if dane.pozycje is not None else szablon.pozycje
    data_poczatku_docelowa = zmiany.get("data_poczatku", szablon.data_poczatku)
    data_konca_docelowa = zmiany.get("data_konca", szablon.data_konca)
    blad = _zwaliduj_ksztalt_szablonu(
        typ_docelowy, pozycje_docelowe, data_poczatku_docelowa, data_konca_docelowa
    )
    if blad is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=blad)

    for pole, wartosc in zmiany.items():
        setattr(szablon, pole, wartosc)

    if dane.pozycje is not None:
        szablon.pozycje.clear()
        db.flush()
        szablon.pozycje.extend(
            PozycjaSzablonuCyklicznego(
                nazwa=p.nazwa,
                ilosc=p.ilosc,
                jednostka_miary=p.jednostka_miary,
                cena_netto_grosze=p.cena_netto_grosze,
                stawka_vat=p.stawka_vat,
            )
            for p in dane.pozycje
        )

    db.commit()
    db.refresh(szablon)
    return szablon


def zmien_status_szablonu(
    db: Session, szablon_id: int, nowy_status: StatusSzablonuCyklicznego
) -> SzablonCykliczny:
    szablon = pobierz_szablon(db, szablon_id)
    szablon.status = nowy_status
    db.commit()
    db.refresh(szablon)
    return szablon


def historia_faktur_szablonu(db: Session, szablon_id: int) -> list[Faktura]:
    pobierz_szablon(db, szablon_id)  # 404, jesli szablon nie istnieje
    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje), selectinload(Faktura.platnosci))
        .where(Faktura.szablon_cykliczny_id == szablon_id)
        .order_by(Faktura.okres_cykliczny.desc())
    )
    return list(db.execute(zapytanie).scalars().unique().all())


def znajdz_zalegle(db: Session, dzisiaj: date | None = None) -> list[ZaleglaFakturaCykliczna]:
    """Wszystkie terminy aktywnych szablonow <= dzisiaj, dla ktorych faktura
    jeszcze nie powstala. Jesli appka nie byla uruchamiana od miesiecy,
    zwraca WSZYSTKIE zalegle terminy (nie tylko ostatni) - patrz
    wygeneruj_terminy, ktora liczy pelen kalendarz od data_poczatku."""
    dzisiaj = dzisiaj or date.today()
    szablony = lista_szablonow(db, tylko_aktywne=True)

    wynik: list[ZaleglaFakturaCykliczna] = []
    for szablon in szablony:
        terminy = wygeneruj_terminy(szablon, dzisiaj)
        if not terminy:
            continue
        wygenerowane = _juz_wygenerowane_terminy(db, szablon.id)
        kwota_szacowana = _oszacuj_sume_brutto_grosze(szablon.pozycje)
        for termin in terminy:
            if termin in wygenerowane:
                continue
            wynik.append(
                ZaleglaFakturaCykliczna(
                    szablon_id=szablon.id,
                    klient_id=szablon.klient_id,
                    klient_nazwa=szablon.klient.nazwa,
                    typ_dokumentu=szablon.typ_dokumentu,
                    okres=termin,
                    waluta=szablon.waluta,
                    kwota_brutto_szacowana_grosze=kwota_szacowana,
                )
            )
    wynik.sort(key=lambda z: z.okres)
    return wynik


def _pobierz_kurs_dla_generowania(waluta: str, okres: date) -> Decimal:
    if waluta == "PLN":
        return Decimal("1")
    try:
        kurs, _data_efektywna = nbp_service.pobierz_kurs_przed_data(waluta, okres)
        return kurs
    except HTTPException:
        # Offline-first (CLAUDE.md/Faza 14): brak polaczenia z NBP nie moze
        # zablokowac wygenerowania roboczej faktury - uzytkownik i tak
        # przeglada/poprawia ja przed wystawieniem, wiec kurs=1 tu jest
        # tylko wartoscia startowa do recznej korekty.
        return Decimal("1")


def generuj_fakture_z_szablonu(db: Session, szablon: SzablonCykliczny, okres: date) -> Faktura:
    kurs_waluty = _pobierz_kurs_dla_generowania(szablon.waluta, okres)

    dane = FakturaCreate(
        typ_dokumentu=szablon.typ_dokumentu,
        klient_id=szablon.klient_id,
        data_wystawienia=okres,
        data_sprzedazy=okres,
        waluta=szablon.waluta,
        kurs_waluty=kurs_waluty,
        pozycje=[
            PozycjaFakturyCreate(
                nazwa=p.nazwa,
                ilosc=p.ilosc,
                jednostka_miary=p.jednostka_miary,
                cena_netto_grosze=p.cena_netto_grosze,
                stawka_vat=p.stawka_vat,
            )
            for p in szablon.pozycje
        ],
    )
    faktura = faktury_service.utworz_fakture(db, dane)
    faktura.szablon_cykliczny_id = szablon.id
    faktura.okres_cykliczny = okres
    db.commit()
    db.refresh(faktura)
    return faktura


def generuj_faktury(
    db: Session, wybory: list[tuple[int, date]] | None
) -> list[Faktura]:
    """`wybory`: lista (szablon_id, okres) do wygenerowania, albo None - wtedy
    generujemy WSZYSTKIE aktualnie zalegle terminy wszystkich aktywnych
    szablonow ("Wygeneruj wszystkie" w oknie startowym)."""
    if wybory is None:
        zalegle = znajdz_zalegle(db)
        wybory = [(z.szablon_id, z.okres) for z in zalegle]

    wygenerowane: list[Faktura] = []
    for szablon_id, okres in wybory:
        szablon = db.execute(
            select(SzablonCykliczny)
            .options(selectinload(SzablonCykliczny.pozycje))
            .where(SzablonCykliczny.id == szablon_id)
        ).scalar_one_or_none()
        if szablon is None:
            continue  # szablon mogl zostac miedzyczasie usuniety/nie istnieje

        # Zabezpieczenie przed podwojnym wygenerowaniem tego samego okresu
        # (np. dwuklik na "Wygeneruj wszystkie").
        juz_istnieje = db.execute(
            select(Faktura.id).where(
                Faktura.szablon_cykliczny_id == szablon_id,
                Faktura.okres_cykliczny == okres,
            )
        ).scalar_one_or_none()
        if juz_istnieje is not None:
            continue

        wygenerowane.append(generuj_fakture_z_szablonu(db, szablon, okres))

    return wygenerowane
