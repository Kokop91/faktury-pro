"""Odczyt plikow CSV do importu (Faza 26) - wspolna infrastruktura dla
gui/windows/dialog_importu_klientow.py i dialog_importu_produktow.py. Reuzywa
wylacznie wbudowany modul `csv` (jak eksport w gui/eksport_csv.py z Fazy 10),
bez nowych zaleznosci.
"""

import csv

_TLUMACZENIE_DIAKRYTYKOW = str.maketrans("ąćęłńóśźż", "acelnoszz")


def normalizuj(tekst: str) -> str:
    """'Miejscowość' -> 'miejscowosc' - do porownan bez wzgledu na wielkosc
    liter i polskie znaki diakrytyczne (naglowki CSV z rownych zrodel pisza
    je rozmaicie: 'Miejscowosc', 'MIEJSCOWOŚĆ', 'miasto'...)."""
    return tekst.strip().lower().translate(_TLUMACZENIE_DIAKRYTYKOW)


class BladOdczytuCsv(Exception):
    pass


def wczytaj_csv(sciezka: str) -> tuple[list[str], list[list[str]]]:
    """Wczytuje plik CSV, zwraca (naglowki, wiersze_danych) - wiersze danych
    jako listy surowego tekstu (naglowek juz wydzielony osobno). NIE zaklada
    sztywnego formatu: separator wykrywany przez csv.Sniffer (domyslnie
    srednik, zgodnie z eksportem appki z Fazy 10, gdy wykrycie zawiedzie na
    zbyt malej/niejednoznacznej probce), kodowanie probowane po kolei
    (utf-8-sig najpierw - tak eksportuje appka i wiekszosc arkuszy kalkulacyjnych
    z ustawieniami PL, potem cp1250 - typowe dla starszych plikow z polskich
    programow ksiegowych)."""
    tresc: str | None = None
    for kodowanie in ("utf-8-sig", "cp1250"):
        try:
            with open(sciezka, "r", newline="", encoding=kodowanie) as plik:
                tresc = plik.read()
            break
        except UnicodeDecodeError:
            continue
        except OSError as e:
            raise BladOdczytuCsv(f"Nie udało się odczytać pliku: {e}") from e

    if tresc is None:
        raise BladOdczytuCsv(
            "Nie udało się odczytać pliku - nieobsługiwane kodowanie znaków."
        )

    probka = tresc[:4096]
    try:
        dialekt = csv.Sniffer().sniff(probka, delimiters=";,\t")
    except csv.Error:
        dialekt = csv.excel
        dialekt.delimiter = ";"

    czytelnik = csv.reader(tresc.splitlines(), dialect=dialekt)
    wszystkie_wiersze = [w for w in czytelnik if any(pole.strip() for pole in w)]
    if not wszystkie_wiersze:
        raise BladOdczytuCsv("Plik CSV jest pusty.")

    naglowki = [n.strip() for n in wszystkie_wiersze[0]]
    if len(set(naglowki)) != len(naglowki):
        raise BladOdczytuCsv(
            "Nagłówki kolumn w pliku powtarzają się - popraw plik, żeby każda "
            "kolumna miała unikalną nazwę."
        )

    return naglowki, wszystkie_wiersze[1:]


def auto_dopasuj_kolumny(
    pola: list[tuple[str, str, bool, tuple[str, ...]]], naglowki: list[str]
) -> dict[str, str]:
    """Zgaduje mapowanie naglowek_csv -> klucz_pola na podstawie nazwy kolumny
    (dokladne dopasowanie do klucza/aliasu pierwszenstwo, potem dopasowanie
    czesciowe) - tylko wygodny punkt startowy do recznej korekty w kroku
    mapowania, nigdy jedyne zrodlo prawdy o mapowaniu."""
    znormalizowane = {naglowek: normalizuj(naglowek) for naglowek in naglowki}
    uzyte: set[str] = set()
    mapowanie: dict[str, str] = {}

    for klucz, _etykieta, _wymagane, aliasy in pola:
        kandydaci = (klucz,) + tuple(aliasy)
        dopasowany = None

        for naglowek, znorm in znormalizowane.items():
            if naglowek in uzyte:
                continue
            if znorm in kandydaci:
                dopasowany = naglowek
                break

        if dopasowany is None:
            for naglowek, znorm in znormalizowane.items():
                if naglowek in uzyte:
                    continue
                if any(alias and (alias in znorm or znorm in alias) for alias in kandydaci):
                    dopasowany = naglowek
                    break

        if dopasowany:
            mapowanie[klucz] = dopasowany
            uzyte.add(dopasowany)

    return mapowanie
