import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    DokumentKosztowy,
    DokumentMagazynowy,
    Faktura,
    KosztReczny,
    PozycjaDokumentuMagazynowego,
    Produkt,
)
from app.models.enums import StatusFaktury, TypDokumentuMagazynowego
from app.schemas.rentownosc import (
    KubelekPrognozyOut,
    MarzaOkresuOut,
    PozycjaPrognozyOut,
    PrognozaWplywowOut,
    PunktWykresuPrzychodKosztOut,
    RentownoscProduktuOut,
)
from app.services import platnosci as platnosci_service

# Mirror app/services/dashboard_service.py:STATUSY_WYLACZONE_Z_PRZYCHODU - swiadomie
# zduplikowane (nie importowane stamtad), zeby uniknac cyklicznego importu
# (dashboard_service importuje ten modul dla kafelka marzy/wykresu).
STATUSY_WYLACZONE_Z_PRZYCHODU = frozenset({StatusFaktury.ROBOCZA, StatusFaktury.ANULOWANA})

LICZBA_MIESIECY_WYKRESU = 12

ETYKIETY_KUBELKOW_PROGNOZY = ["Do 30 dni", "31-60 dni", "61-90 dni", "Powyżej 90 dni"]


def _pierwszy_dzien_miesiaca(d: date) -> date:
    return d.replace(day=1)


def _przesun_miesiace(d: date, delta: int) -> date:
    indeks = d.year * 12 + (d.month - 1) + delta
    return date(indeks // 12, indeks % 12 + 1, 1)


def _ostatni_dzien_miesiaca(rok: int, miesiac: int) -> date:
    return date(rok, miesiac, calendar.monthrange(rok, miesiac)[1])


def _zaokraglij_do_grosza(wartosc: Decimal) -> int:
    return int(wartosc.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def zakres_dat(rok: int, miesiac: int | None, wariant: str) -> tuple[date, date]:
    if wariant == "miesieczny":
        if miesiac is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wariant 'miesieczny' wymaga podania miesiaca.",
            )
        return date(rok, miesiac, 1), _ostatni_dzien_miesiaca(rok, miesiac)

    if wariant == "kwartalny":
        if miesiac is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wariant 'kwartalny' wymaga podania miesiaca (dowolnego z kwartalu).",
            )
        pierwszy_miesiac_kwartalu = (miesiac - 1) // 3 * 3 + 1
        ostatni_miesiac_kwartalu = pierwszy_miesiac_kwartalu + 2
        return (
            date(rok, pierwszy_miesiac_kwartalu, 1),
            _ostatni_dzien_miesiaca(rok, ostatni_miesiac_kwartalu),
        )

    if wariant == "roczny":
        return date(rok, 1, 1), date(rok, 12, 31)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Nieznany wariant okresu: '{wariant}'.",
    )


def _przychod_netto_grosze(db: Session, data_od: date, data_do: date) -> int:
    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje))
        .where(
            Faktura.status.notin_(STATUSY_WYLACZONE_Z_PRZYCHODU),
            Faktura.data_wystawienia >= data_od,
            Faktura.data_wystawienia <= data_do,
        )
    )
    faktury = db.execute(zapytanie).scalars().unique().all()
    return sum(f.suma_netto_grosze for f in faktury)


def _pozycje_pz_z_cena_zakupu(
    db: Session, data_od: date, data_do: date
) -> list[tuple[PozycjaDokumentuMagazynowego, date]]:
    """Pozycje PZ z opcjonalnie wpisana cena zakupu netto (Faza 27), w podanym
    okresie (wg daty dokumentu PZ). Zwraca pary (pozycja, data_dokumentu) -
    wykres_przychody_koszty potrzebuje daty do przypisania do kubelka miesiaca,
    marza_okresu jej nie potrzebuje, ale nie ma sensu pytac baze dwa razy."""
    zapytanie = (
        select(PozycjaDokumentuMagazynowego, DokumentMagazynowy.data_dokumentu)
        .join(DokumentMagazynowy, PozycjaDokumentuMagazynowego.dokument_id == DokumentMagazynowy.id)
        .where(
            DokumentMagazynowy.typ == TypDokumentuMagazynowego.PZ,
            PozycjaDokumentuMagazynowego.cena_zakupu_netto_grosze.is_not(None),
            DokumentMagazynowy.data_dokumentu >= data_od,
            DokumentMagazynowy.data_dokumentu <= data_do,
        )
    )
    return list(db.execute(zapytanie).all())


def _koszt_pozycji_pz_grosze(pozycja: PozycjaDokumentuMagazynowego) -> int:
    return _zaokraglij_do_grosza(Decimal(pozycja.cena_zakupu_netto_grosze) * pozycja.ilosc)


def marza_okresu(db: Session, data_od: date, data_do: date) -> MarzaOkresuOut:
    przychod_netto_grosze = _przychod_netto_grosze(db, data_od, data_do)

    dokumenty_kosztowe = list(
        db.execute(
            select(DokumentKosztowy).where(
                DokumentKosztowy.data_wystawienia >= data_od,
                DokumentKosztowy.data_wystawienia <= data_do,
            )
        )
        .scalars()
        .all()
    )
    koszty_ksef_grosze = sum(d.netto_grosze for d in dokumenty_kosztowe)

    koszty_reczne = list(
        db.execute(
            select(KosztReczny).where(
                KosztReczny.data >= data_od, KosztReczny.data <= data_do
            )
        )
        .scalars()
        .all()
    )
    koszty_reczne_grosze = sum(k.kwota_grosze for k in koszty_reczne)

    pozycje_pz = _pozycje_pz_z_cena_zakupu(db, data_od, data_do)
    koszty_pz_grosze = sum(_koszt_pozycji_pz_grosze(pozycja) for pozycja, _data in pozycje_pz)

    ma_dane_kosztowe = bool(dokumenty_kosztowe or koszty_reczne or pozycje_pz)
    koszty_razem_grosze = koszty_ksef_grosze + koszty_reczne_grosze + koszty_pz_grosze
    marza_grosze = przychod_netto_grosze - koszty_razem_grosze
    marza_procent = (
        (marza_grosze / przychod_netto_grosze) * 100
        if ma_dane_kosztowe and przychod_netto_grosze > 0
        else None
    )

    return MarzaOkresuOut(
        przychod_netto_grosze=przychod_netto_grosze,
        koszty_ksef_grosze=koszty_ksef_grosze,
        koszty_reczne_grosze=koszty_reczne_grosze,
        koszty_pz_grosze=koszty_pz_grosze,
        koszty_razem_grosze=koszty_razem_grosze,
        marza_grosze=marza_grosze,
        marza_procent=marza_procent,
        ma_dane_kosztowe=ma_dane_kosztowe,
    )


def wykres_przychody_koszty(
    db: Session,
    dzisiaj: date | None = None,
    miesiace: int = LICZBA_MIESIECY_WYKRESU,
    faktury: list[Faktura] | None = None,
) -> list[PunktWykresuPrzychodKosztOut]:
    """`faktury` pozwala wywolujacemu (dashboard_service.pobierz_dashboard)
    podac juz zaladowana (ten sam zakres dat, ten sam filtr statusu) liste
    faktur zamiast zlecac tu drugie, identyczne zapytanie + hydratacje ORM -
    na dashboardzie z wieksza iloscia faktur to byl mierzalnie najdrozszy
    pojedynczy krok calego ladowania. Domyslne None (zapytaj sama) zostaje
    dla wywolan bez juz zaladowanych danych."""
    dzisiaj = dzisiaj or date.today()
    poczatek_biezacego_miesiaca = _pierwszy_dzien_miesiaca(dzisiaj)
    poczatek_okna = _przesun_miesiace(poczatek_biezacego_miesiaca, -(miesiace - 1))

    kubelki_przychodu: dict[tuple[int, int], int] = {}
    kubelki_kosztow: dict[tuple[int, int], int] = {}
    kursor = poczatek_okna
    for _ in range(miesiace):
        kubelki_przychodu[(kursor.year, kursor.month)] = 0
        kubelki_kosztow[(kursor.year, kursor.month)] = 0
        kursor = _przesun_miesiace(kursor, 1)

    if faktury is None:
        faktury = (
            db.execute(
                select(Faktura)
                .options(selectinload(Faktura.pozycje))
                .where(
                    Faktura.status.notin_(STATUSY_WYLACZONE_Z_PRZYCHODU),
                    Faktura.data_wystawienia >= poczatek_okna,
                )
            )
            .scalars()
            .unique()
            .all()
        )
    for faktura in faktury:
        klucz = (faktura.data_wystawienia.year, faktura.data_wystawienia.month)
        if klucz in kubelki_przychodu:
            kubelki_przychodu[klucz] += faktura.suma_netto_grosze

    dokumenty_kosztowe = (
        db.execute(
            select(DokumentKosztowy).where(DokumentKosztowy.data_wystawienia >= poczatek_okna)
        )
        .scalars()
        .all()
    )
    for dokument in dokumenty_kosztowe:
        klucz = (dokument.data_wystawienia.year, dokument.data_wystawienia.month)
        if klucz in kubelki_kosztow:
            kubelki_kosztow[klucz] += dokument.netto_grosze

    koszty_reczne = (
        db.execute(select(KosztReczny).where(KosztReczny.data >= poczatek_okna))
        .scalars()
        .all()
    )
    for koszt in koszty_reczne:
        klucz = (koszt.data.year, koszt.data.month)
        if klucz in kubelki_kosztow:
            kubelki_kosztow[klucz] += koszt.kwota_grosze

    pozycje_pz = _pozycje_pz_z_cena_zakupu(db, poczatek_okna, dzisiaj)
    for pozycja, data_dokumentu in pozycje_pz:
        klucz = (data_dokumentu.year, data_dokumentu.month)
        if klucz in kubelki_kosztow:
            kubelki_kosztow[klucz] += _koszt_pozycji_pz_grosze(pozycja)

    return [
        PunktWykresuPrzychodKosztOut(
            rok=rok,
            miesiac=miesiac,
            przychod_netto_grosze=kubelki_przychodu[(rok, miesiac)],
            koszty_grosze=kubelki_kosztow[(rok, miesiac)],
        )
        for (rok, miesiac) in sorted(kubelki_przychodu.keys())
    ]


def _kubelek_indeks(dni_do_terminu: int) -> int:
    if dni_do_terminu <= 30:
        return 0
    if dni_do_terminu <= 60:
        return 1
    if dni_do_terminu <= 90:
        return 2
    return 3


def _srednie_opoznienia_per_klient(db: Session) -> dict[int, float]:
    """Sredni czas platnosci (dni po terminie, moze byc ujemny = wczesniej)
    per klient, liczony wylacznie z faktur JUZ w pelni oplaconych - faktura
    czesciowo oplacona nie ma jeszcze "daty ostatecznego rozliczenia"."""
    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.platnosci))
        .where(Faktura.status == StatusFaktury.OPLACONA)
    )
    faktury = db.execute(zapytanie).scalars().unique().all()

    opoznienia_per_klient: dict[int, list[int]] = {}
    for faktura in faktury:
        if not faktura.platnosci:
            continue
        ostatnia_platnosc = max(p.data_platnosci for p in faktura.platnosci)
        opoznienie_dni = (ostatnia_platnosc - faktura.termin_platnosci).days
        opoznienia_per_klient.setdefault(faktura.klient_id, []).append(opoznienie_dni)

    return {
        klient_id: sum(wartosci) / len(wartosci)
        for klient_id, wartosci in opoznienia_per_klient.items()
    }


def prognoza_wplywow(db: Session, dzisiaj: date | None = None) -> PrognozaWplywowOut:
    dzisiaj = dzisiaj or date.today()
    opoznienia_per_klient = _srednie_opoznienia_per_klient(db)

    faktury_naleznosci, _suma = platnosci_service.lista_naleznosci(db, dzisiaj)

    kubelki_podstawowe = [0, 0, 0, 0]
    kubelki_skorygowane = [0, 0, 0, 0]
    pozycje: list[PozycjaPrognozyOut] = []

    for faktura in faktury_naleznosci:
        kwota_pozostala = faktura.kwota_pozostala_grosze
        if kwota_pozostala <= 0:
            continue

        termin_bazowy = faktura.termin_platnosci
        opoznienie_srednie = opoznienia_per_klient.get(faktura.klient_id, 0.0)
        termin_skorygowany = termin_bazowy + timedelta(days=round(opoznienie_srednie))

        dni_bazowe = (termin_bazowy - dzisiaj).days
        dni_skorygowane = (termin_skorygowany - dzisiaj).days
        kubelki_podstawowe[_kubelek_indeks(dni_bazowe)] += kwota_pozostala
        kubelki_skorygowane[_kubelek_indeks(dni_skorygowane)] += kwota_pozostala

        pozycje.append(
            PozycjaPrognozyOut(
                faktura_id=faktura.id,
                numer=faktura.numer,
                klient_nazwa=faktura.klient.nazwa,
                kwota_pozostala_grosze=kwota_pozostala,
                waluta=faktura.waluta,
                termin_bazowy=termin_bazowy,
                termin_skorygowany=termin_skorygowany,
            )
        )

    return PrognozaWplywowOut(
        kubelki_podstawowe=[
            KubelekPrognozyOut(etykieta=etykieta, kwota_grosze=kwota)
            for etykieta, kwota in zip(ETYKIETY_KUBELKOW_PROGNOZY, kubelki_podstawowe)
        ],
        kubelki_skorygowane=[
            KubelekPrognozyOut(etykieta=etykieta, kwota_grosze=kwota)
            for etykieta, kwota in zip(ETYKIETY_KUBELKOW_PROGNOZY, kubelki_skorygowane)
        ],
        pozycje=pozycje,
    )


def rentownosc_produktow(
    db: Session, data_od: date, data_do: date
) -> list[RentownoscProduktuOut]:
    produkty_z_kosztem = (
        db.execute(select(Produkt).where(Produkt.koszt_zakupu_grosze.is_not(None)))
        .scalars()
        .all()
    )
    produkty_wg_nazwy = {p.nazwa.strip().lower(): p for p in produkty_z_kosztem}
    if not produkty_wg_nazwy:
        return []

    faktury = (
        db.execute(
            select(Faktura)
            .options(selectinload(Faktura.pozycje))
            .where(
                Faktura.status.notin_(STATUSY_WYLACZONE_Z_PRZYCHODU),
                Faktura.data_wystawienia >= data_od,
                Faktura.data_wystawienia <= data_do,
            )
        )
        .scalars()
        .unique()
        .all()
    )

    agregaty: dict[int, dict] = {}
    for faktura in faktury:
        for pozycja in faktura.pozycje:
            produkt = produkty_wg_nazwy.get(pozycja.nazwa.strip().lower())
            if produkt is None:
                continue
            wpis = agregaty.setdefault(
                produkt.id,
                {
                    "produkt": produkt,
                    "ilosc": Decimal("0"),
                    "przychod_netto_grosze": 0,
                    "koszt_grosze": 0,
                },
            )
            wpis["ilosc"] += pozycja.ilosc
            wpis["przychod_netto_grosze"] += pozycja.wartosc_netto_grosze
            wpis["koszt_grosze"] += _zaokraglij_do_grosza(
                Decimal(produkt.koszt_zakupu_grosze) * pozycja.ilosc
            )

    wyniki = []
    for wpis in agregaty.values():
        marza_grosze = wpis["przychod_netto_grosze"] - wpis["koszt_grosze"]
        marza_procent = (
            (marza_grosze / wpis["przychod_netto_grosze"]) * 100
            if wpis["przychod_netto_grosze"] > 0
            else None
        )
        wyniki.append(
            RentownoscProduktuOut(
                produkt_id=wpis["produkt"].id,
                nazwa=wpis["produkt"].nazwa,
                jednostka_miary=wpis["produkt"].jednostka_miary,
                ilosc_sprzedana=wpis["ilosc"],
                przychod_netto_grosze=wpis["przychod_netto_grosze"],
                koszt_grosze=wpis["koszt_grosze"],
                marza_grosze=marza_grosze,
                marza_procent=marza_procent,
            )
        )

    wyniki.sort(key=lambda w: w.marza_grosze, reverse=True)
    return wyniki
