"""Mapowanie modelu Faktura (Etap 1) na strukture logiczna FA(3) i walidacja
wygenerowanego XML wzgledem oficjalnego schematu XSD Ministerstwa Finansow
(Faza 12B).

ZRODLO: github.com/CIRFMF/ksef-api, katalog faktury/schemy/FA, plik
schemat_FA3_v1-0E.xsd (kopia w app/xsd/fa3/, sciezka importu StrukturyDanych
poprawiona na lokalna - patrz komentarz w tym pliku). Struktura pol
zweryfikowana bezposrednio z tresci XSD 2026-07-15, NIE zgadywana.

Zakres (Faza 12B): RodzajFaktury = VAT / ZAL / ROZ / KOR / KOR_ZAL / KOR_ROZ,
odpowiadajace typom dokumentu FAKTURA_VAT / FAKTURA_ZALICZKOWA /
FAKTURA_KONCOWA / FAKTURA_KORYGUJACA. Swiadomie POMIJA (jako opcjonalne w
XSD i nieuzywane przez model danych appki): Platnosc, WarunkiTransakcji,
Zamowienie, Rozliczenie, Podmiot3, PodmiotUpowazniony, GTU/Procedura,
oznaczenia specjalne poza MPP (marza, nowe srodki transportu, TP) - wszystkie
te pola sa opcjonalne w schemacie, wiec ich pominiecie nie narusza poprawnosci
dokumentu dla zwyklej krajowej sprzedazy towarow/uslug. P_18A (mechanizm
podzielonej platnosci) jest polem WYMAGANYM w schemacie (nie opcjonalnym) i
mapowany jest z Faktura.wymaga_mpp od Fazy 21 (app/services/mpp_service.py).

WAZNE OGRANICZENIE: pozycje ze stawka VAT "zw" (zwolnione) sa CELOWO
zablokowane (patrz KsefKwalifikowalnoscError w _sprawdz_kwalifikowalnosc) -
FA(3) wymaga w takim przypadku wskazania podstawy prawnej zwolnienia
(pole P_19A/P_19B/P_19C), a model danych appki (Firma/Faktura) nie zbiera
dotychczas takiej informacji. Wysylka takich faktur (w tym typu RACHUNEK,
ktory z definicji jest w calosci "zw") wymaga najpierw dodania tego pola -
zgloszone uzytkownikowi, nie zgadywane.
"""
import base64
import hashlib
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources

from lxml import etree

from app.models.enums import StawkaVat, TypDokumentu
from app.models.faktura import Faktura
from app.services.ksef_kody_krajow import NieznanyKodKrajuError, kod_kraju

TNS = "http://crd.gov.pl/wzor/2025/06/25/13775/"
NSMAP = {None: TNS}

_XSD_DIR = resources.files("app.xsd.fa3")
_XSD_GLOWNY = "schemat_FA3_v1-0E.xsd"

# Mapowanie TypDokumentu -> RodzajFaktury zalezy od korygowanego typu dla
# FAKTURA_KORYGUJACA, wiec ustalane jest funkcja (_rodzaj_faktury), nie
# statycznym slownikiem.
_STAWKA_NA_KOD_FA3: dict[StawkaVat, str] = {
    StawkaVat.STAWKA_23: "23",
    StawkaVat.STAWKA_8: "8",
    StawkaVat.STAWKA_5: "5",
    StawkaVat.STAWKA_0: "0 KR",
    StawkaVat.ZW: "zw",
}


class KsefKwalifikowalnoscError(Exception):
    """Dokument nie moze byc w ogole wyslany do KSeF (np. proforma, nota
    korygujaca, albo brakujace dane wymagane przez FA(3))."""


class Fa3WalidacjaError(Exception):
    """Wygenerowany XML nie przeszedl walidacji wzgledem schematu XSD.
    `bledy` to lista czytelnych komunikatow (jeden na kazdy blad walidatora)."""

    def __init__(self, bledy: list[str]):
        super().__init__("; ".join(bledy))
        self.bledy = bledy


def _wczytaj_schemat() -> etree.XMLSchema:
    with resources.as_file(_XSD_DIR / _XSD_GLOWNY) as sciezka:
        doc = etree.parse(str(sciezka))
    return etree.XMLSchema(doc)


def _kwota(grosze: int) -> str:
    return str((Decimal(grosze) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _sub(parent: etree._Element, tag: str, tekst: str | None = None, **attrs) -> etree._Element:
    el = etree.SubElement(parent, f"{{{TNS}}}{tag}")
    if tekst is not None:
        el.text = tekst
    for klucz, wartosc in attrs.items():
        el.set(klucz, wartosc)
    return el


def _rodzaj_faktury(faktura: Faktura) -> str:
    if faktura.typ_dokumentu in (TypDokumentu.FAKTURA_VAT, TypDokumentu.RACHUNEK):
        return "VAT"
    if faktura.typ_dokumentu == TypDokumentu.FAKTURA_ZALICZKOWA:
        return "ZAL"
    if faktura.typ_dokumentu == TypDokumentu.FAKTURA_KONCOWA:
        return "ROZ"
    if faktura.typ_dokumentu == TypDokumentu.FAKTURA_KORYGUJACA:
        typ_korygowanego = faktura.dokument_powiazany.typ_dokumentu
        if typ_korygowanego == TypDokumentu.FAKTURA_ZALICZKOWA:
            return "KOR_ZAL"
        if typ_korygowanego == TypDokumentu.FAKTURA_KONCOWA:
            return "KOR_ROZ"
        return "KOR"
    raise KsefKwalifikowalnoscError(
        f"Dokument typu '{faktura.typ_dokumentu.value}' nie ma odpowiednika "
        "w strukturze FA(3) i nie moze byc wyslany do KSeF."
    )


def _sprawdz_kwalifikowalnosc(faktura: Faktura) -> None:
    if faktura.typ_dokumentu in (TypDokumentu.PROFORMA, TypDokumentu.NOTA_KORYGUJACA):
        nazwa = "Faktura pro forma" if faktura.typ_dokumentu == TypDokumentu.PROFORMA else "Nota korygująca"
        raise KsefKwalifikowalnoscError(
            f"{nazwa} nie jest fakturą w rozumieniu ustawy o VAT i nie ma żadnej "
            "reprezentacji w strukturze FA(3) - KSeF jej nie obsługuje. Ten typ "
            "dokumentu nigdy nie jest wysyłany do KSeF."
        )

    if any(p.stawka_vat == StawkaVat.ZW for p in faktura.pozycje):
        raise KsefKwalifikowalnoscError(
            "Faktura zawiera pozycje ze stawką VAT 'zw' (zwolnione z VAT). "
            "Struktura FA(3) wymaga w takim przypadku wskazania podstawy prawnej "
            "zwolnienia, a aplikacja nie zbiera jeszcze tej informacji - wysyłka "
            "takich faktur do KSeF nie jest obecnie obsługiwana."
        )

    if faktura.typ_dokumentu in (
        TypDokumentu.FAKTURA_KORYGUJACA,
        TypDokumentu.FAKTURA_KONCOWA,
    ) and faktura.dokument_powiazany is None:
        raise KsefKwalifikowalnoscError(
            "Brak dokumentu powiązanego - nie można zbudować struktury FA(3)."
        )


def _zbuduj_naglowek(root: etree._Element) -> None:
    naglowek = _sub(root, "Naglowek")
    _sub(naglowek, "KodFormularza", "FA", kodSystemowy="FA (3)", wersjaSchemy="1-0E")
    _sub(naglowek, "WariantFormularza", "3")
    teraz = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _sub(naglowek, "DataWytworzeniaFa", teraz)


def _zbuduj_adres(parent: etree._Element, ulica, kod_pocztowy, miejscowosc, kraj) -> None:
    adres = _sub(parent, "Adres")
    try:
        kod = kod_kraju(kraj or "Polska")
    except NieznanyKodKrajuError as e:
        raise KsefKwalifikowalnoscError(str(e)) from e
    _sub(adres, "KodKraju", kod)
    linia1 = ulica or miejscowosc or "-"
    _sub(adres, "AdresL1", linia1[:512])
    linia2_czesci = [kod_pocztowy, miejscowosc] if ulica else []
    linia2 = " ".join(czesc for czesc in linia2_czesci if czesc)
    if linia2:
        _sub(adres, "AdresL2", linia2[:512])


def _zbuduj_podmiot1(root: etree._Element, firma) -> None:
    podmiot1 = _sub(root, "Podmiot1")
    dane = _sub(podmiot1, "DaneIdentyfikacyjne")
    _sub(dane, "NIP", firma.nip)
    _sub(dane, "Nazwa", firma.nazwa[:512])
    _zbuduj_adres(podmiot1, firma.ulica, firma.kod_pocztowy, firma.miejscowosc, firma.kraj)


def _zbuduj_podmiot2(root: etree._Element, klient) -> None:
    podmiot2 = _sub(root, "Podmiot2")
    dane = _sub(podmiot2, "DaneIdentyfikacyjne")
    if klient.nip:
        _sub(dane, "NIP", klient.nip)
    else:
        _sub(dane, "BrakID", "1")
    _sub(dane, "Nazwa", klient.nazwa[:512])
    if klient.ulica or klient.miejscowosc or klient.kod_pocztowy:
        _zbuduj_adres(podmiot2, klient.ulica, klient.kod_pocztowy, klient.miejscowosc, klient.kraj)
    _sub(podmiot2, "JST", "2")
    _sub(podmiot2, "GV", "2")


def _grupy_stawek(pozycje) -> dict[str, dict[str, int]]:
    grupy: dict[str, dict[str, int]] = {}
    for pozycja in pozycje:
        wpis = grupy.setdefault(
            pozycja.stawka_vat, {"netto_grosze": 0, "vat_grosze": 0}
        )
        wpis["netto_grosze"] += pozycja.wartosc_netto_grosze
        wpis["vat_grosze"] += pozycja.wartosc_vat_grosze
    return grupy


def _zbuduj_fa(root: etree._Element, faktura: Faktura) -> None:
    fa = _sub(root, "Fa")
    _sub(fa, "KodWaluty", faktura.waluta)
    _sub(fa, "P_1", faktura.data_wystawienia.isoformat())
    _sub(fa, "P_2", faktura.numer)
    _sub(fa, "P_6", faktura.data_sprzedazy.isoformat())

    grupy = _grupy_stawek(faktura.pozycje)
    if StawkaVat.STAWKA_23 in grupy:
        _sub(fa, "P_13_1", _kwota(grupy[StawkaVat.STAWKA_23]["netto_grosze"]))
        _sub(fa, "P_14_1", _kwota(grupy[StawkaVat.STAWKA_23]["vat_grosze"]))
    if StawkaVat.STAWKA_8 in grupy:
        _sub(fa, "P_13_2", _kwota(grupy[StawkaVat.STAWKA_8]["netto_grosze"]))
        _sub(fa, "P_14_2", _kwota(grupy[StawkaVat.STAWKA_8]["vat_grosze"]))
    if StawkaVat.STAWKA_5 in grupy:
        _sub(fa, "P_13_3", _kwota(grupy[StawkaVat.STAWKA_5]["netto_grosze"]))
        _sub(fa, "P_14_3", _kwota(grupy[StawkaVat.STAWKA_5]["vat_grosze"]))
    if StawkaVat.STAWKA_0 in grupy:
        _sub(fa, "P_13_6_1", _kwota(grupy[StawkaVat.STAWKA_0]["netto_grosze"]))
    # StawkaVat.ZW zablokowane wczesniej w _sprawdz_kwalifikowalnosc.

    _sub(fa, "P_15", _kwota(faktura.suma_brutto_grosze))
    if faktura.waluta != "PLN":
        _sub(fa, "KursWalutyZ", str(faktura.kurs_waluty))

    adnotacje = _sub(fa, "Adnotacje")
    _sub(adnotacje, "P_16", "2")
    _sub(adnotacje, "P_17", "2")
    _sub(adnotacje, "P_18", "2")
    # Faza 21 - mechanizm podzielonej platnosci (art. 106e ust. 1 pkt 18a
    # ustawy o VAT). "1" gdy Faktura.wymaga_mpp, w przeciwnym razie "2" -
    # pole wymagane w schemacie (nie minOccurs=0), KSeF waliduje jego obecnosc.
    _sub(adnotacje, "P_18A", "1" if faktura.wymaga_mpp else "2")
    zwolnienie = _sub(adnotacje, "Zwolnienie")
    _sub(zwolnienie, "P_19N", "1")
    nowe_srodki = _sub(adnotacje, "NoweSrodkiTransportu")
    _sub(nowe_srodki, "P_22N", "1")
    _sub(adnotacje, "P_23", "2")
    pmarzy = _sub(adnotacje, "PMarzy")
    _sub(pmarzy, "P_PMarzyN", "1")

    _sub(fa, "RodzajFaktury", _rodzaj_faktury(faktura))

    if faktura.typ_dokumentu == TypDokumentu.FAKTURA_KORYGUJACA:
        korygowana = faktura.dokument_powiazany
        _sub(fa, "PrzyczynaKorekty", (faktura.przyczyna_korekty or "")[:256])
        dane_korygowanej = _sub(fa, "DaneFaKorygowanej")
        _sub(dane_korygowanej, "DataWystFaKorygowanej", korygowana.data_wystawienia.isoformat())
        _sub(dane_korygowanej, "NrFaKorygowanej", korygowana.numer)
        if korygowana.numer_ksef:
            _sub(dane_korygowanej, "NrKSeF", "1")
            _sub(dane_korygowanej, "NrKSeFFaKorygowanej", korygowana.numer_ksef)
        else:
            _sub(dane_korygowanej, "NrKSeFN", "1")

    if faktura.typ_dokumentu == TypDokumentu.FAKTURA_KONCOWA:
        zaliczkowa = faktura.dokument_powiazany
        faktura_zaliczkowa = _sub(fa, "FakturaZaliczkowa")
        if zaliczkowa.numer_ksef:
            _sub(faktura_zaliczkowa, "NrKSeFFaZaliczkowej", zaliczkowa.numer_ksef)
        else:
            _sub(faktura_zaliczkowa, "NrKSeFZN", "1")
            _sub(faktura_zaliczkowa, "NrFaZaliczkowej", zaliczkowa.numer)

    for i, pozycja in enumerate(faktura.pozycje, start=1):
        wiersz = _sub(fa, "FaWiersz")
        _sub(wiersz, "NrWierszaFa", str(i))
        _sub(wiersz, "P_7", pozycja.nazwa[:512])
        _sub(wiersz, "P_8A", pozycja.jednostka_miary)
        _sub(wiersz, "P_8B", str(pozycja.ilosc))
        _sub(wiersz, "P_9A", _kwota(pozycja.cena_netto_grosze))
        _sub(wiersz, "P_11", _kwota(pozycja.wartosc_netto_grosze))
        _sub(wiersz, "P_12", _STAWKA_NA_KOD_FA3[pozycja.stawka_vat])


def zbuduj_fa3_xml(faktura: Faktura) -> bytes:
    """Buduje dokument XML FA(3) dla podanej faktury (relacje klient/pozycje/
    dokument_powiazany/firma musza byc juz zaladowane - zob. wywolujacy w
    ksef_service.py). Rzuca KsefKwalifikowalnoscError, jesli dokumentu nie da
    sie w ogole wyslac (np. proforma, brakujace dane)."""
    _sprawdz_kwalifikowalnosc(faktura)
    firma = faktura.klient.firma

    root = etree.Element(f"{{{TNS}}}Faktura", nsmap=NSMAP)
    _zbuduj_naglowek(root)
    _zbuduj_podmiot1(root, firma)
    _zbuduj_podmiot2(root, faktura.klient)
    _zbuduj_fa(root, faktura)

    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=False
    )


def waliduj_fa3_xml(xml_bytes: bytes) -> None:
    """Waliduje surowy XML wzgledem oficjalnego schematu FA(3). Rzuca
    Fa3WalidacjaError z lista czytelnych komunikatow (pole + opis bledu),
    jesli dokument nie jest zgodny ze schematem - NIC nie jest wtedy wysylane."""
    schemat = _wczytaj_schemat()
    dokument = etree.fromstring(xml_bytes)
    if not schemat.validate(dokument):
        bledy = [
            f"linia {blad.line}: {blad.message}" for blad in schemat.error_log
        ]
        raise Fa3WalidacjaError(bledy)


def sha256_base64(dane: bytes) -> str:
    return base64.b64encode(hashlib.sha256(dane).digest()).decode("ascii")
