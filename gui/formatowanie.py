from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

ETYKIETY_STATUSU: dict[str, str] = {
    "robocza": "Robocza",
    "wystawiona": "Wystawiona",
    "wyslana": "Wysłana",
    "oplacona_czesciowo": "Opłacona częściowo",
    "oplacona": "Opłacona",
    "po_terminie": "Po terminie",
    "anulowana": "Anulowana",
}

ETYKIETY_TYPU_DOKUMENTU: dict[str, str] = {
    "faktura_vat": "Faktura VAT",
    "proforma": "Faktura pro forma",
    "faktura_zaliczkowa": "Faktura zaliczkowa",
    "faktura_koncowa": "Faktura rozliczeniowa (końcowa)",
    "faktura_korygujaca": "Faktura korygująca",
    "nota_korygujaca": "Nota korygująca",
    "rachunek": "Rachunek",
}

# Typy wymagajace dokument_powiazany_id / przyczyna_korekty (mirror
# app/models/enums.py TYPY_WYMAGAJACE_DOKUMENTU_POWIAZANEGO / _PRZYCZYNY_KOREKTY) -
# zduplikowane w GUI bo to osobny proces, nie importujemy z app/.
TYPY_WYMAGAJACE_DOKUMENTU_POWIAZANEGO: frozenset[str] = frozenset(
    {"faktura_korygujaca", "nota_korygujaca", "faktura_koncowa"}
)
TYPY_WYMAGAJACE_PRZYCZYNY_KOREKTY: frozenset[str] = frozenset(
    {"faktura_korygujaca", "nota_korygujaca"}
)
DOZWOLONE_TYPY_DOKUMENTU_KORYGOWANEGO: frozenset[str] = frozenset(
    {"faktura_vat", "faktura_zaliczkowa", "faktura_koncowa", "rachunek"}
)

KOLEJNOSC_STAWEK_VAT: list[str] = ["23", "8", "5", "0", "zw"]

ETYKIETY_STAWEK_VAT: dict[str, str] = {
    "23": "23%",
    "8": "8%",
    "5": "5%",
    "0": "0%",
    "zw": "zw.",
}

# Mirror UDZIAL_STAWKI_VAT z app/services/faktury.py - do wizualnego podgladu sum
# w formularzu, backend i tak przelicza ostatecznie po swojej stronie.
UDZIAL_STAWKI_VAT: dict[str, Decimal] = {
    "23": Decimal("0.23"),
    "8": Decimal("0.08"),
    "5": Decimal("0.05"),
    "0": Decimal("0"),
    "zw": Decimal("0"),
}


def formatuj_status(status: str) -> str:
    return ETYKIETY_STATUSU.get(status, status)


def formatuj_typ_dokumentu(typ: str) -> str:
    return ETYKIETY_TYPU_DOKUMENTU.get(typ, typ)


def formatuj_kwote(grosze: int, waluta: str = "PLN") -> str:
    """Formatuje grosze (int) do postaci '1 234,56 PLN'. Arytmetyka calkowita
    (bez dzielenia float), zeby pieniadze nie stracily precyzji nawet w prezentacji.
    """
    ujemna = grosze < 0
    grosze = abs(grosze)
    zlote, reszta_groszy = divmod(grosze, 100)

    tekst_zlotych = f"{zlote:,}".replace(",", " ")
    wynik = f"{tekst_zlotych},{reszta_groszy:02d} {waluta}"
    return f"-{wynik}" if ujemna else wynik


def formatuj_date(wartosc) -> str:
    if wartosc is None:
        return ""
    if isinstance(wartosc, str):
        try:
            wartosc = date.fromisoformat(wartosc[:10])
        except ValueError:
            return wartosc
    if isinstance(wartosc, datetime):
        wartosc = wartosc.date()
    return wartosc.strftime("%d.%m.%Y")


def _zaokraglij_do_grosza(wartosc: Decimal) -> int:
    return int(wartosc.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def oblicz_podglad_pozycji(
    cena_netto_grosze: int, ilosc: Decimal, stawka_vat: str
) -> tuple[int, int, int]:
    """Podglad przeliczenia pozycji faktury (netto/vat/brutto w groszach) - mirror
    logiki zaokraglania z app/services/faktury.py. Czysto wizualne w formularzu,
    backend i tak przelicza ostatecznie po swojej stronie."""
    netto = _zaokraglij_do_grosza(Decimal(cena_netto_grosze) * ilosc)
    vat = _zaokraglij_do_grosza(Decimal(netto) * UDZIAL_STAWKI_VAT[stawka_vat])
    brutto = netto + vat
    return netto, vat, brutto


def parsuj_kwote(tekst: str) -> int:
    """Parsuje '1234,56' / '1234.56' / '1234' na grosze (int, > 0). Rzuca ValueError
    z czytelnym polskim komunikatem przy nieprawidlowych danych."""
    tekst = tekst.strip().replace(" ", "").replace(",", ".")
    if not tekst:
        raise ValueError("kwota jest wymagana")
    try:
        wartosc = Decimal(tekst)
    except InvalidOperation:
        raise ValueError("nieprawidłowa kwota") from None
    grosze = _zaokraglij_do_grosza(wartosc * 100)
    if grosze <= 0:
        raise ValueError("kwota musi być większa od zera")
    return grosze


def parsuj_liczbe_dodatnia(tekst: str, nazwa_pola: str = "wartość") -> Decimal:
    """Ogolny parser dodatniej liczby dziesietnej ('2' / '2,5' / '2.5') z komunikatem
    bledu dopasowanym do nazwy pola (np. 'ilość', 'kurs waluty'). Rzuca ValueError."""
    tekst = tekst.strip().replace(" ", "").replace(",", ".")
    if not tekst:
        raise ValueError(f"{nazwa_pola} jest wymagana(y)")
    try:
        wartosc = Decimal(tekst)
    except InvalidOperation:
        raise ValueError(f"nieprawidłowa wartość pola „{nazwa_pola}”") from None
    if wartosc <= 0:
        raise ValueError(f"{nazwa_pola} musi być większa(y) od zera")
    return wartosc


def parsuj_ilosc(tekst: str) -> Decimal:
    """Parsuje ilość ('2' / '2,5' / '2.5') na Decimal > 0. Rzuca ValueError."""
    return parsuj_liczbe_dodatnia(tekst, "ilość")


def parsuj_date_pl(tekst: str) -> date:
    """Parsuje date w formacie 'DD.MM.RRRR' (zgodnym z formatuj_date). Rzuca ValueError."""
    tekst = tekst.strip()
    try:
        return datetime.strptime(tekst, "%d.%m.%Y").date()
    except ValueError:
        raise ValueError("data musi być w formacie DD.MM.RRRR") from None


def grosze_do_wpisu(grosze: int) -> str:
    """Grosze -> tekst do pola edytowalnego, np. '123,45' (bez waluty, do pre-fill
    formularza) - w odroznieniu od formatuj_kwote, ktora jest tylko do wyswietlania."""
    zlote, reszta = divmod(abs(grosze), 100)
    tekst = f"{zlote},{reszta:02d}"
    return f"-{tekst}" if grosze < 0 else tekst
