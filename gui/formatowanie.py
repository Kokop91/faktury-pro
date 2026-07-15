from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from gui import styl

ETYKIETY_STATUSU: dict[str, str] = {
    "robocza": "Robocza",
    "wystawiona": "Wystawiona",
    "wyslana": "Wysłana",
    "oplacona_czesciowo": "Opłacona częściowo",
    "oplacona": "Opłacona",
    "po_terminie": "Po terminie",
    "anulowana": "Anulowana",
}

ETYKIETY_STATUSU_DOKUMENTU_KOSZTOWEGO: dict[str, str] = {
    "nowa": "Nowa",
    "zaakceptowana": "Zaakceptowana",
    "do_wyjasnienia": "Do wyjaśnienia",
}

ETYKIETY_STATUSU_KSEF: dict[str, str] = {
    "nie_wyslana": "Nie wysłana",
    "wysylanie_w_toku": "Wysyłanie w toku",
    "przyjeta": "Przyjęta",
    "odrzucona": "Odrzucona",
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

ETYKIETY_TYPU_DOKUMENTU_MAGAZYNOWEGO: dict[str, str] = {
    "pz": "PZ — Przyjęcie zewnętrzne",
    "wz": "WZ — Wydanie zewnętrzne",
    "pw": "PW — Przyjęcie wewnętrzne",
    "rw": "RW — Rozchód wewnętrzny",
    "mm": "MM — Przesunięcie międzymagazynowe",
}

KOLEJNOSC_TYPOW_DOKUMENTU_MAGAZYNOWEGO: list[str] = ["pz", "wz", "pw", "rw", "mm"]

# Ktory z (magazyn_zrodlowy, magazyn_docelowy) jest wymagany dla danego typu -
# mirror app/services/magazyn_service.py WYMAGANE_MAGAZYNY, zduplikowane w GUI
# (osobny proces), zeby formularz mogl pokazywac/ukrywac wlasciwe pola bez
# czekania na blad z backendu.
WYMAGANE_MAGAZYNY_DOKUMENTU: dict[str, tuple[bool, bool]] = {
    "pz": (False, True),
    "wz": (True, False),
    "pw": (False, True),
    "rw": (True, False),
    "mm": (True, True),
}

ETYKIETY_STATUSU_INWENTARYZACJI: dict[str, str] = {
    "w_trakcie": "W trakcie",
    "zakonczona": "Zakończona",
}

ETYKIETY_CZESTOTLIWOSCI: dict[str, str] = {
    "miesieczna": "Miesięczna",
    "kwartalna": "Kwartalna",
    "roczna": "Roczna",
}
KOLEJNOSC_CZESTOTLIWOSCI: list[str] = ["miesieczna", "kwartalna", "roczna"]

ETYKIETY_STATUSU_SZABLONU: dict[str, str] = {
    "aktywny": "Aktywny",
    "wstrzymany": "Wstrzymany",
}

# Typy dozwolone jako szablon cykliczny (mirror
# app/models/enums.py DOZWOLONE_TYPY_SZABLONU_CYKLICZNEGO) - korekty/noty/
# faktury koncowe odnosza sie zawsze do jednego, konkretnego dokumentu, wiec
# nie moga byc szablonem.
DOZWOLONE_TYPY_SZABLONU_CYKLICZNEGO: frozenset[str] = frozenset(
    {"faktura_vat", "proforma", "faktura_zaliczkowa", "rachunek"}
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


def kolor_statusu(status: str) -> str:
    return styl.KOLORY_STATUSU.get(status, styl.KOLOR_TEKST_GLOWNY)


def formatuj_typ_dokumentu(typ: str) -> str:
    return ETYKIETY_TYPU_DOKUMENTU.get(typ, typ)


def formatuj_status_dokumentu_kosztowego(status: str) -> str:
    return ETYKIETY_STATUSU_DOKUMENTU_KOSZTOWEGO.get(status, status)


def kolor_statusu_dokumentu_kosztowego(status: str) -> tuple[str, str]:
    # nowa=zolty/pomaranczowy (wymaga uwagi), zaakceptowana=zielony,
    # do_wyjasnienia=czerwony - ta sama konwencja co status_ksef.
    return {
        "nowa": styl.KOLOR_OSTRZEZENIE,
        "zaakceptowana": styl.KOLOR_SUKCES,
        "do_wyjasnienia": styl.KOLOR_BLAD,
    }.get(status, styl.KOLOR_TEKST_DRUGORZEDNY)


def formatuj_status_ksef(status_ksef: str) -> str:
    return ETYKIETY_STATUSU_KSEF.get(status_ksef, status_ksef)


def kolor_statusu_ksef(status_ksef: str) -> tuple[str, str]:
    # (jasny, ciemny) zgodnie z konwencja styl.py - zielony=przyjeta,
    # czerwony=odrzucona, zolty/pomaranczowy=w toku, szary=jeszcze nie wyslana.
    return {
        "przyjeta": styl.KOLOR_SUKCES,
        "odrzucona": styl.KOLOR_BLAD,
        "wysylanie_w_toku": styl.KOLOR_OSTRZEZENIE,
    }.get(status_ksef, styl.KOLOR_TEKST_DRUGORZEDNY)


def formatuj_typ_dokumentu_magazynowego(typ: str) -> str:
    return ETYKIETY_TYPU_DOKUMENTU_MAGAZYNOWEGO.get(typ, typ)


def formatuj_status_inwentaryzacji(status: str) -> str:
    return ETYKIETY_STATUSU_INWENTARYZACJI.get(status, status)


def kolor_statusu_inwentaryzacji(status: str) -> str:
    return styl.KOLOR_OSTRZEZENIE if status == "w_trakcie" else styl.KOLOR_SUKCES


def formatuj_czestotliwosc(czestotliwosc: str) -> str:
    return ETYKIETY_CZESTOTLIWOSCI.get(czestotliwosc, czestotliwosc)


def formatuj_status_szablonu(status: str) -> str:
    return ETYKIETY_STATUSU_SZABLONU.get(status, status)


def kolor_statusu_szablonu(status: str) -> str:
    # Wstrzymanie jest normalnym, celowym dzialaniem uzytkownika - nie
    # ostrzegawczy kolor, tylko neutralny (w odroznieniu np. od "po terminie").
    return styl.KOLOR_SUKCES if status == "aktywny" else styl.KOLOR_TEKST_DRUGORZEDNY


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


def formatuj_data_czas(wartosc) -> str:
    """Data + godzina (Faza 14: znacznik czasu weryfikacji bialej listy VAT -
    ma znaczenie dowodowe, wiec sama data bez godziny by nie wystarczyla)."""
    if wartosc is None:
        return ""
    if isinstance(wartosc, str):
        try:
            wartosc = datetime.fromisoformat(wartosc)
        except ValueError:
            return wartosc
    return wartosc.strftime("%d.%m.%Y %H:%M")


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


def parsuj_kwote(tekst: str, wymagaj_dodatniej: bool = True) -> int:
    """Parsuje '1234,56' / '1234.56' / '1234' na grosze (int). Domyslnie wymaga
    kwoty > 0 (faktury/platnosci); `wymagaj_dodatniej=False` dopuszcza takze 0
    (np. domyslna cena produktu w katalogu, gdzie backend przyjmuje ge=0).
    Rzuca ValueError z czytelnym polskim komunikatem przy nieprawidlowych danych."""
    tekst = tekst.strip().replace(" ", "").replace(",", ".")
    if not tekst:
        raise ValueError("kwota jest wymagana")
    try:
        wartosc = Decimal(tekst)
    except InvalidOperation:
        raise ValueError("nieprawidłowa kwota") from None
    grosze = _zaokraglij_do_grosza(wartosc * 100)
    if wymagaj_dodatniej and grosze <= 0:
        raise ValueError("kwota musi być większa od zera")
    if grosze < 0:
        raise ValueError("kwota nie może być ujemna")
    return grosze


def parsuj_liczbe_dodatnia(
    tekst: str, nazwa_pola: str = "wartość", wymagaj_dodatniej: bool = True
) -> Decimal:
    """Ogolny parser liczby dziesietnej ('2' / '2,5' / '2.5') z komunikatem bledu
    dopasowanym do nazwy pola (np. 'ilość', 'kurs waluty'). Domyslnie wymaga > 0;
    `wymagaj_dodatniej=False` dopuszcza takze 0 (np. stan faktyczny przy spisie
    inwentaryzacyjnym - produkt moze byc calkowicie wyczerpany). Rzuca ValueError."""
    tekst = tekst.strip().replace(" ", "").replace(",", ".")
    if not tekst:
        raise ValueError(f"{nazwa_pola} jest wymagana(y)")
    try:
        wartosc = Decimal(tekst)
    except InvalidOperation:
        raise ValueError(f"nieprawidłowa wartość pola „{nazwa_pola}”") from None
    if wymagaj_dodatniej and wartosc <= 0:
        raise ValueError(f"{nazwa_pola} musi być większa(y) od zera")
    if wartosc < 0:
        raise ValueError(f"{nazwa_pola} nie może być ujemna(y)")
    return wartosc


def parsuj_ilosc(tekst: str) -> Decimal:
    """Parsuje ilość ('2' / '2,5' / '2.5') na Decimal > 0. Rzuca ValueError."""
    return parsuj_liczbe_dodatnia(tekst, "ilość")


def formatuj_ilosc(wartosc, jednostka: str | None = None) -> str:
    """Formatuje ilosc (Decimal albo string z API, np. '100.000') do postaci
    '100' / '2,5' - bez zbednych zer, z przecinkiem zamiast kropki."""
    try:
        liczba = Decimal(str(wartosc))
    except InvalidOperation:
        return str(wartosc)
    tekst = format(liczba.normalize(), "f")
    if "." not in tekst:
        tekst_wynik = tekst
    else:
        calosc, ulamek = tekst.split(".")
        tekst_wynik = f"{calosc},{ulamek}" if int(ulamek) != 0 else calosc
    return f"{tekst_wynik} {jednostka}" if jednostka else tekst_wynik


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
