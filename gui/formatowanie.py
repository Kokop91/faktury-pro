from datetime import date, datetime

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
