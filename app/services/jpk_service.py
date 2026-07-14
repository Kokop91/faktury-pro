"""Generowanie JPK_V7M(3) / JPK_V7K(3) - Faza 13.

Struktura XML oparta WYLACZNIE na oficjalnym schemacie XSD Ministerstwa
Finansow, pobranym z Centralnego Repozytorium Wzorow Dokumentow
Elektronicznych (crd.gov.pl) i zbadanym programowo (nie z pamieci) przed
napisaniem tego pliku:
  - JPK_V7M(3): http://crd.gov.pl/wzor/2025/12/19/14090/
  - JPK_V7K(3): http://crd.gov.pl/wzor/2025/12/19/14089/
Oba warianty obowiazuja od 1 lutego 2026 (integracja z KSeF). Pliki XSD (wraz
z zaimportowanymi schematami wspoldzielonymi) sa dolaczone lokalnie w
app/jpk_schemas/ - wygenerowany XML jest zawsze walidowany wzgledem NICH
(offline, bez zadnego zapytania sieciowego) przed zwroceniem do uzytkownika.

WAZNE OGRANICZENIA WYNIKAJACE Z ZAKRESU APLIKACJI (opisane tez w GUI):
1. Appka NIE ma modulu zakupow/kosztow - sekcja Ewidencja/Zakup jest zawsze
   pusta (0 wierszy, PodatekNaliczony=0.00 - to POPRAWNY, zgodny ze
   schematem stan, patrz adnotacja tego pola w XSD). W konsekwencji P_51
   (kwota do zaplaty) pokazuje CALY VAT nalezny ze sprzedazy, bez
   pomniejszenia o VAT naliczony z zakupow - ksiegowa MUSI doliczyc
   odliczenia recznie przed wyslaniem pliku do urzedu.
2. Appka nie integruje sie z KSeF (Faza 12 nieukonczona) - kazdy wiersz
   ewidencji oznaczany jest jako BFK ("Faktura elektroniczna lub faktura w
   postaci papierowej"), zgodnie z definicja tego pola w XSD.
3. Appka obsluguje wylacznie krajowa sprzedaz opodatkowana stawkami
   23/8/5/0% oraz zwolniona (K_10/K_13/K_15-16/K_17-18/K_19-20) - nie ma
   sprzedazy zagranicznej, WDT, eksportu ani importu, wiec pozostale pola
   K_/P_ (K_11,K_12,K_14,K_21-K_36 i odpowiadajace P_) sa zawsze nieobecne.
4. Nie obslugujemy zlozenia korygujacego (CelZlozenia=2) ani wniosku o
   zwrot/przeksiegowanie nadwyzki (P_54 i nastepne) - appka generuje zawsze
   pierwsze zlozenie za dany okres bez wnioskowania o zwrot.
"""
import json
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import lxml.etree as ET
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura, Firma
from app.models.enums import StatusFaktury, StawkaVat, TypDokumentu, TypPodatnika

SCHEMATY_DIR = Path(__file__).resolve().parent.parent / "jpk_schemas"

# Namespace wspoldzielonych typow bazowych (etd:) z StrukturyDanych.xsd. Element
# formDefault="qualified" oznacza, ze elementy odziedziczone przez OsobaFizyczna
# z etd:TIdentyfikatorOsobyFizycznej2 (NIP/ImiePierwsze/Nazwisko/DataUrodzenia)
# ZACHOWUJA namespace etd:, mimo ze typ jest rozszerzany lokalnie w JPK_V7M/K.xsd -
# w odroznieniu od OsobaNiefizyczna, ktorej bazowy typ jest zdefiniowany LOKALNIE
# (w namespace tns: danego wariantu), wiec jej NIP/PelnaNazwa zostaja w tns:.
NS_ETD = "http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/09/13/eD/DefinicjeTypy/"

WARIANTY: dict[str, dict[str, str]] = {
    "miesieczny": {
        "ns": "http://crd.gov.pl/wzor/2025/12/19/14090/",
        "kod_systemowy": "JPK_V7M (3)",
        "xsd": "JPK_V7M3.xsd",
        # Deklaracja (VAT-7) - wartosci rozne dla wariantu kwartalnego (VAT-7K),
        # patrz TKodFormularzaVAT7/TKodFormularzaVATK w bundlowanym XSD.
        "kod_formularza_dekl": "VAT-7",
        "kod_systemowy_dekl": "VAT-7 (23)",
        "wariant_formularza_dekl": "23",
    },
    "kwartalny": {
        "ns": "http://crd.gov.pl/wzor/2025/12/19/14089/",
        "kod_systemowy": "JPK_V7K (3)",
        "xsd": "JPK_V7K3.xsd",
        "kod_formularza_dekl": "VAT-7K",
        "kod_systemowy_dekl": "VAT-7K (17)",
        "wariant_formularza_dekl": "17",
    },
}

# Typy dokumentu z realnym skutkiem podatkowym (musza pojawic sie w
# ewidencji). Proforma nie jest dokumentem podatkowym; nota korygujaca
# koryguje wylacznie dane formalne (np. literowke w nazwie), nie kwoty.
TYPY_W_EWIDENCJI: frozenset[TypDokumentu] = frozenset(
    {
        TypDokumentu.FAKTURA_VAT,
        TypDokumentu.FAKTURA_ZALICZKOWA,
        TypDokumentu.FAKTURA_KONCOWA,
        TypDokumentu.FAKTURA_KORYGUJACA,
        TypDokumentu.RACHUNEK,
    }
)
# "Robocza" nie ma jeszcze mocy prawnej (nie zostala wystawiona), "anulowana"
# zostala wycofana - obie pomijane w faktycznej ewidencji, ale zglaszane
# uzytkownikowi jako ostrzezenie PRZED wygenerowaniem (patrz sprawdz_gotowosc_okresu).
STATUSY_POMIJANE: frozenset[StatusFaktury] = frozenset(
    {StatusFaktury.ROBOCZA, StatusFaktury.ANULOWANA}
)

# Mapowanie stawki VAT z modelu PozycjaFaktury na pola ewidencji (K_) -
# (pole podstawy, pole podatku albo None dla stawek bez podatku naleznego).
MAPOWANIE_STAWEK_K: dict[StawkaVat, tuple[str, str | None]] = {
    StawkaVat.ZW: ("K_10", None),
    StawkaVat.STAWKA_0: ("K_13", None),
    StawkaVat.STAWKA_5: ("K_15", "K_16"),
    StawkaVat.STAWKA_8: ("K_17", "K_18"),
    StawkaVat.STAWKA_23: ("K_19", "K_20"),
}
# To samo, ale pola deklaracji (P_) - uzywane przy sumowaniu do Deklaracji.
MAPOWANIE_STAWEK_P: dict[StawkaVat, tuple[str, str | None]] = {
    StawkaVat.ZW: ("P_10", None),
    StawkaVat.STAWKA_0: ("P_13", None),
    StawkaVat.STAWKA_5: ("P_15", "P_16"),
    StawkaVat.STAWKA_8: ("P_17", "P_18"),
    StawkaVat.STAWKA_23: ("P_19", "P_20"),
}

_schematy_cache: dict[str, ET.XMLSchema] = {}
_urzedy_skarbowe_cache: list[dict[str, str]] | None = None


def lista_urzedow_skarbowych() -> list[dict[str, str]]:
    """Zwraca oficjalna liste 4-cyfrowych kodow urzedow skarbowych (wyodrebniona
    z enumeracji w bundlowanym XSD) - uzywana w GUI jako zrodlo picker'a, zeby
    uzytkownik nie musial zgadywac poprawnego kodu na pamiec."""
    global _urzedy_skarbowe_cache
    if _urzedy_skarbowe_cache is None:
        with open(SCHEMATY_DIR / "urzedy_skarbowe.json", encoding="utf-8") as plik:
            dane = json.load(plik)
        _urzedy_skarbowe_cache = [
            {"kod": kod, "nazwa": nazwa} for kod, nazwa in sorted(dane.items(), key=lambda kv: kv[1])
        ]
    return _urzedy_skarbowe_cache


def _wczytaj_schema(nazwa_pliku: str) -> ET.XMLSchema:
    if nazwa_pliku not in _schematy_cache:
        dokument = ET.parse(str(SCHEMATY_DIR / nazwa_pliku))
        _schematy_cache[nazwa_pliku] = ET.XMLSchema(dokument)
    return _schematy_cache[nazwa_pliku]


def _zakres_miesiaca(rok: int, miesiac: int) -> tuple[date, date]:
    pierwszy = date(rok, miesiac, 1)
    if miesiac == 12:
        ostatni = date(rok, 12, 31)
    else:
        ostatni = date(rok, miesiac + 1, 1) - timedelta(days=1)
    return pierwszy, ostatni


def _faktury_okresu(db: Session, rok: int, miesiac: int) -> list[Faktura]:
    pierwszy, ostatni = _zakres_miesiaca(rok, miesiac)
    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje), selectinload(Faktura.klient))
        .where(Faktura.data_wystawienia >= pierwszy, Faktura.data_wystawienia <= ostatni)
        .order_by(Faktura.data_wystawienia, Faktura.numer)
    )
    return list(db.execute(zapytanie).scalars().unique().all())


def sprawdz_gotowosc_okresu(db: Session, rok: int, miesiac: int) -> dict:
    """Sprawdzenie PRZED generowaniem (wymagane w GUI) - zwraca liste
    problemow (faktury robocze / bez NIP klienta), zeby uzytkownik mogl je
    poprawic zamiast dostac po cichu niepelny/bledny plik."""
    faktury = [f for f in _faktury_okresu(db, rok, miesiac) if f.typ_dokumentu in TYPY_W_EWIDENCJI]

    problemy: list[dict] = []
    liczba_do_ujecia = 0
    for faktura in faktury:
        if faktura.status == StatusFaktury.ROBOCZA:
            problemy.append(
                {
                    "faktura_id": faktura.id,
                    "numer": faktura.numer,
                    "klient_nazwa": faktura.klient.nazwa,
                    "problem": "robocza",
                }
            )
            continue
        if faktura.status == StatusFaktury.ANULOWANA:
            continue
        liczba_do_ujecia += 1
        if not (faktura.klient.nip and faktura.klient.nip.strip()):
            problemy.append(
                {
                    "faktura_id": faktura.id,
                    "numer": faktura.numer,
                    "klient_nazwa": faktura.klient.nazwa,
                    "problem": "brak_nip_klienta",
                }
            )

    return {"liczba_faktur_do_ujecia": liczba_do_ujecia, "problemy": problemy}


def _pobierz_firme(db: Session) -> Firma:
    firmy = list(db.execute(select(Firma)).scalars().all())
    if len(firmy) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dane firmy nie są skonfigurowane - uzupełnij je w Ustawieniach przed generowaniem JPK.",
        )
    return firmy[0]


def _waliduj_dane_firmy(firma: Firma) -> None:
    brakujace: list[str] = []
    if not firma.kod_urzedu_skarbowego:
        brakujace.append("kod urzędu skarbowego")
    # Email jest WYMAGANY w sekcji Podmiot1 (zarowno OsobaFizyczna jak i
    # OsobaNiefizyczna) - wynika to z lokalnej definicji TPodmiotDowolnyBezAdresu
    # w samym schemacie JPK_V7M3/V7K3.xsd (rozszerza wspoldzielony typ o
    # wymagany Email + opcjonalny Telefon), nie ze wspoldzielonych typow w
    # StrukturyDanych.xsd.
    if not firma.email:
        brakujace.append("adres e-mail")
    if firma.typ_podatnika == TypPodatnika.OSOBA_FIZYCZNA:
        if not firma.imie_pierwsze:
            brakujace.append("imię")
        if not firma.nazwisko:
            brakujace.append("nazwisko")
        if not firma.data_urodzenia:
            brakujace.append("data urodzenia")
    if brakujace:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Dane firmy są niekompletne do wygenerowania JPK - uzupełnij w Ustawieniach: "
                + ", ".join(brakujace) + "."
            ),
        )


def _czy_dolaczyc_deklaracje(wariant: str, miesiac: int) -> bool:
    """Deklaracja (podsumowanie VAT-7) jest skladana co miesiac dla wariantu
    miesiecznego, a dla kwartalnego TYLKO w ostatnim miesiacu kwartalu
    (3/6/9/12) - w pozostalych miesiacach kwartalnik wysyla samą Ewidencję.
    To nie jest zalozenie - wynika wprost ze struktury schematu (Deklaracja
    ma minOccurs=0 w obu wariantach; Naglowek obu wariantow uzywa pola
    Miesiac, nie Kwartal - kwartalnik i tak rozlicza sie co miesiac, tylko
    podsumowanie VAT-7 skalda raz na kwartal)."""
    if wariant == "miesieczny":
        return True
    return miesiac % 3 == 0


def _kwota_k(grosze: int) -> str:
    """Pola K_ (ewidencja): 2 miejsca po przecinku, dokladna wartosc zlotowa."""
    return str((Decimal(grosze) / 100).quantize(Decimal("0.01")))


def _kwota_p(grosze: int) -> str:
    """Pola P_ (deklaracja): pelne zlote, zaokraglenie wg art. 63 Ordynacji
    podatkowej (koncowki < 50 gr w dol, >= 50 gr w gore = ROUND_HALF_UP na
    poziomie pojedynczego zlotego)."""
    return str((Decimal(grosze) / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _dodaj(parent, ns: str, tag: str, tekst: str | None = None):
    element = ET.SubElement(parent, _q(ns, tag))
    if tekst is not None:
        element.text = tekst
    return element


def _dodaj_naglowek(root, ns: str, kod_systemowy: str, rok: int, miesiac: int, kod_urzedu: str) -> None:
    nag = _dodaj(root, ns, "Naglowek")
    kf = _dodaj(nag, ns, "KodFormularza", "JPK_VAT")
    kf.set("kodSystemowy", kod_systemowy)
    kf.set("wersjaSchemy", "1-0E")
    _dodaj(nag, ns, "WariantFormularza", "3")
    _dodaj(nag, ns, "DataWytworzeniaJPK", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    _dodaj(nag, ns, "NazwaSystemu", "Faktury Pro")
    cel = _dodaj(nag, ns, "CelZlozenia", "1")
    cel.set("poz", "P_7")
    _dodaj(nag, ns, "KodUrzedu", kod_urzedu)
    _dodaj(nag, ns, "Rok", str(rok))
    _dodaj(nag, ns, "Miesiac", str(miesiac))


def _dodaj_podmiot1(root, ns: str, firma: Firma) -> None:
    # Uwaga: lokalna definicja Podmiot1 w tym schemacie NIE ma pola REGON dla
    # OsobaNiefizyczna (w odroznieniu od ogolnego typu etd:TIdentyfikatorOsobyNiefizycznej
    # ze StrukturyDanych.xsd) - za to obie odmiany wymagaja Email i opcjonalnego Telefonu.
    podmiot = _dodaj(root, ns, "Podmiot1")
    podmiot.set("rola", "Podatnik")
    if firma.typ_podatnika == TypPodatnika.OSOBA_FIZYCZNA:
        osoba = _dodaj(podmiot, ns, "OsobaFizyczna")
        _dodaj(osoba, NS_ETD, "NIP", firma.nip)
        _dodaj(osoba, NS_ETD, "ImiePierwsze", firma.imie_pierwsze)
        _dodaj(osoba, NS_ETD, "Nazwisko", firma.nazwisko)
        _dodaj(osoba, NS_ETD, "DataUrodzenia", firma.data_urodzenia.isoformat())
    else:
        osoba = _dodaj(podmiot, ns, "OsobaNiefizyczna")
        _dodaj(osoba, ns, "NIP", firma.nip)
        _dodaj(osoba, ns, "PelnaNazwa", firma.nazwa)
    _dodaj(osoba, ns, "Email", firma.email)
    if firma.telefon:
        _dodaj(osoba, ns, "Telefon", firma.telefon)


def _pozycje_wg_stawki(faktura: Faktura) -> dict[StawkaVat, tuple[int, int]]:
    """Sumuje wartosc netto/VAT (w groszach) pozycji faktury wg stawki."""
    suma: dict[StawkaVat, tuple[int, int]] = {}
    for pozycja in faktura.pozycje:
        netto, vat = suma.get(pozycja.stawka_vat, (0, 0))
        suma[pozycja.stawka_vat] = (
            netto + pozycja.wartosc_netto_grosze,
            vat + pozycja.wartosc_vat_grosze,
        )
    return suma


def _faktury_do_ewidencji(faktury: list[Faktura]) -> list[Faktura]:
    return [
        f for f in faktury if f.typ_dokumentu in TYPY_W_EWIDENCJI and f.status not in STATUSY_POMIJANE
    ]


def _dodaj_sprzedaz_wiersz(ewidencja, ns: str, lp: int, faktura: Faktura) -> None:
    wiersz = _dodaj(ewidencja, ns, "SprzedazWiersz")
    _dodaj(wiersz, ns, "LpSprzedazy", str(lp))
    nip_kontrahenta = faktura.klient.nip.strip() if faktura.klient.nip and faktura.klient.nip.strip() else "brak"
    _dodaj(wiersz, ns, "NrKontrahenta", nip_kontrahenta)
    _dodaj(wiersz, ns, "NazwaKontrahenta", faktura.klient.nazwa)
    _dodaj(wiersz, ns, "DowodSprzedazy", faktura.numer)
    _dodaj(wiersz, ns, "DataWystawienia", faktura.data_wystawienia.isoformat())
    # DataSprzedazy wypelniamy TYLKO gdy rozni sie od DataWystawienia - tak
    # wprost stanowi dokumentacja tego pola w XSD ("W przeciwnym przypadku -
    # pole puste"), pole jest opcjonalne (minOccurs=0).
    if faktura.data_sprzedazy != faktura.data_wystawienia:
        _dodaj(wiersz, ns, "DataSprzedazy", faktura.data_sprzedazy.isoformat())
    # BFK = "Faktura elektroniczna lub faktura w postaci papierowej" - appka
    # nie integruje sie z KSeF (Faza 12 nieukonczona), wiec to jedyny
    # poprawny wybor z czworki NrKSeF/OFF/BFK/DI dla kazdej wystawionej faktury.
    _dodaj(wiersz, ns, "BFK", "1")

    # Kolejnosc iteracji MUSI byc kolejnoscia stawek w schemacie (K_10 < K_13
    # < K_15/16 < K_17/18 < K_19/20) - xsd:sequence wymusza scisla kolejnosc
    # elementow, a kolejnosc pozycji na fakturze jest przypadkowa wzgledem stawek.
    pozycje_wg_stawki = _pozycje_wg_stawki(faktura)
    for stawka, (pole_podstawy, pole_podatku) in MAPOWANIE_STAWEK_K.items():
        netto_grosze, vat_grosze = pozycje_wg_stawki.get(stawka, (0, 0))
        if netto_grosze == 0 and vat_grosze == 0:
            continue
        _dodaj(wiersz, ns, pole_podstawy, _kwota_k(netto_grosze))
        if pole_podatku:
            _dodaj(wiersz, ns, pole_podatku, _kwota_k(vat_grosze))


def _oblicz_sumy_wg_stawki(faktury_do_ewidencji: list[Faktura]) -> dict[StawkaVat, tuple[int, int]]:
    sumy_wg_stawki: dict[StawkaVat, tuple[int, int]] = {}
    for faktura in faktury_do_ewidencji:
        for stawka, (netto, vat) in _pozycje_wg_stawki(faktura).items():
            netto_suma, vat_suma = sumy_wg_stawki.get(stawka, (0, 0))
            sumy_wg_stawki[stawka] = (netto_suma + netto, vat_suma + vat)
    return sumy_wg_stawki


def _dodaj_ewidencje(
    root, ns: str, faktury_do_ewidencji: list[Faktura], sumy_wg_stawki: dict[StawkaVat, tuple[int, int]]
) -> None:
    ewidencja = _dodaj(root, ns, "Ewidencja")

    for lp, faktura in enumerate(faktury_do_ewidencji, start=1):
        _dodaj_sprzedaz_wiersz(ewidencja, ns, lp, faktura)

    # Podatek nalezny wg ewidencji = suma K_16+K_18+K_20 (+K_24.. zawsze 0 w
    # tej appce, patrz MAPOWANIE_STAWEK_K) - patrz adnotacja PodatekNalezny w XSD.
    podatek_nalezny_grosze = sum(
        vat for stawka, (_netto, vat) in sumy_wg_stawki.items() if MAPOWANIE_STAWEK_K[stawka][1]
    )
    ctrl_sprzedaz = _dodaj(ewidencja, ns, "SprzedazCtrl")
    _dodaj(ctrl_sprzedaz, ns, "LiczbaWierszySprzedazy", str(len(faktury_do_ewidencji)))
    _dodaj(ctrl_sprzedaz, ns, "PodatekNalezny", _kwota_k(podatek_nalezny_grosze))

    # Appka nie sledzi zakupow/kosztow (patrz naglowek modulu) - ewidencja
    # zakupu jest zawsze pusta, co jest stanem POPRAWNYM wg schematu.
    ctrl_zakup = _dodaj(ewidencja, ns, "ZakupCtrl")
    _dodaj(ctrl_zakup, ns, "LiczbaWierszyZakupow", "0")
    _dodaj(ctrl_zakup, ns, "PodatekNaliczony", "0.00")


def _dodaj_deklaracje(
    root, ns: str, wariant: str, wariant_info: dict[str, str], miesiac: int,
    sumy_wg_stawki: dict[StawkaVat, tuple[int, int]],
) -> None:
    deklaracja = _dodaj(root, ns, "Deklaracja")
    nag = _dodaj(deklaracja, ns, "Naglowek")
    kfd = _dodaj(nag, ns, "KodFormularzaDekl", wariant_info["kod_formularza_dekl"])
    kfd.set("kodSystemowy", wariant_info["kod_systemowy_dekl"])
    kfd.set("kodPodatku", "VAT")
    kfd.set("rodzajZobowiazania", "Z")
    kfd.set("wersjaSchemy", "1-0E")
    _dodaj(nag, ns, "WariantFormularzaDekl", wariant_info["wariant_formularza_dekl"])
    if wariant == "kwartalny":
        # Naglowek JPK uzywa Miesiac (plik skladany co miesiac), ale sama
        # deklaracja VAT-7K dodatkowo wymaga numeru kwartalu, ktory rozlicza
        # (widoczne tylko w 3./6./9./12. miesiacu, patrz _czy_dolaczyc_deklaracje).
        kwartal = (miesiac - 1) // 3 + 1
        _dodaj(nag, ns, "Kwartal", str(kwartal))

    pozycje = _dodaj(deklaracja, ns, "PozycjeSzczegolowe")

    # Kolejnosc iteracji MUSI byc kolejnoscia stawek w schemacie (P_10 < P_13
    # < P_15/16 < P_17/18 < P_19/20) - patrz analogiczny komentarz w
    # _dodaj_sprzedaz_wiersz.
    suma_vat_nalezny_grosze = 0
    for stawka, (pole_podstawy, pole_podatku) in MAPOWANIE_STAWEK_P.items():
        netto_grosze, vat_grosze = sumy_wg_stawki.get(stawka, (0, 0))
        if netto_grosze == 0 and vat_grosze == 0:
            continue
        _dodaj(pozycje, ns, pole_podstawy, _kwota_p(netto_grosze))
        if pole_podatku:
            _dodaj(pozycje, ns, pole_podatku, _kwota_p(vat_grosze))
            suma_vat_nalezny_grosze += vat_grosze

    # P_38 = suma P_16,P_18,P_20 (+P_24.. zawsze 0 w tej appce) - patrz
    # adnotacja P_38 w XSD. P_51 = P_38 jesli > 0, inaczej 0 (patrz adnotacja
    # P_51) - bez pomniejszenia o VAT naliczony, bo appka nie sledzi zakupow.
    _dodaj(pozycje, ns, "P_38", _kwota_p(suma_vat_nalezny_grosze))
    kwota_do_zaplaty = suma_vat_nalezny_grosze if suma_vat_nalezny_grosze > 0 else 0
    _dodaj(pozycje, ns, "P_51", _kwota_p(kwota_do_zaplaty))

    # Pouczenia: wartosc "1" potwierdza zapoznanie sie z pouczeniami o
    # odpowiedzialnosci karnoskarbowej - wymagane pole, ta sama tresc na
    # kazdym zlozeniu (patrz dokumentacja pola w XSD).
    _dodaj(deklaracja, ns, "Pouczenia", "1")


def generuj_jpk_v7(db: Session, rok: int, miesiac: int, wariant: str) -> bytes:
    if wariant not in WARIANTY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieznany wariant JPK: {wariant} (oczekiwano 'miesieczny' albo 'kwartalny').",
        )
    if not (1 <= miesiac <= 12):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Miesiąc musi być w zakresie 1-12.")

    firma = _pobierz_firme(db)
    _waliduj_dane_firmy(firma)

    info = WARIANTY[wariant]
    ns = info["ns"]

    root = ET.Element(_q(ns, "JPK"), nsmap={None: ns, "etd": NS_ETD})
    _dodaj_naglowek(root, ns, info["kod_systemowy"], rok, miesiac, firma.kod_urzedu_skarbowego)
    _dodaj_podmiot1(root, ns, firma)

    faktury_do_ewidencji = _faktury_do_ewidencji(_faktury_okresu(db, rok, miesiac))
    sumy_wg_stawki = _oblicz_sumy_wg_stawki(faktury_do_ewidencji)

    # Kolejnosc w drzewie MUSI byc Naglowek, Podmiot1, Deklaracja, Ewidencja -
    # tak wynika z xsd:sequence w elemencie JPK (Deklaracja poprzedza Ewidencje).
    if _czy_dolaczyc_deklaracje(wariant, miesiac):
        _dodaj_deklaracje(root, ns, wariant, info, miesiac, sumy_wg_stawki)
    _dodaj_ewidencje(root, ns, faktury_do_ewidencji, sumy_wg_stawki)

    xml_bytes = ET.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    _waliduj_wzgledem_xsd(xml_bytes, info["xsd"])
    return xml_bytes


def _waliduj_wzgledem_xsd(xml_bytes: bytes, nazwa_pliku_xsd: str) -> None:
    schema = _wczytaj_schema(nazwa_pliku_xsd)
    try:
        dokument = ET.fromstring(xml_bytes)
    except ET.XMLSyntaxError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wygenerowany plik JPK nie jest poprawnym XML: {e}",
        ) from e

    if not schema.validate(dokument):
        bledy = "; ".join(str(blad) for blad in schema.error_log)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Wygenerowany plik JPK nie przeszedł walidacji względem oficjalnego "
                f"schematu XSD - plik NIE został udostępniony do pobrania. Szczegóły: {bledy}"
            ),
        )
