import json
import os
from pathlib import Path

# Ustawienia integracji (Faza 14: srodowisko GUS + klucz produkcyjny) trzymane
# lokalnie poza baza danych i poza repozytorium - ten sam wzorzec katalogu co
# haslo appki w gui/auth.py, ale osobny plik i osobny proces (ten kod dziala
# w backendzie/FastAPI, nie w GUI - to backend faktycznie wywoluje SOAP GUS).
NAZWA_KATALOGU = "FakturyPro"
NAZWA_PLIKU = "integracje.json"

DOMYSLNE_SRODOWISKO_GUS = "testowe"
SRODOWISKA_GUS = ("testowe", "produkcyjne")

# Publicznie udokumentowany klucz testowy GUS BIR1.1 - dziala wylacznie
# przeciwko srodowisku testowemu (zwraca ustalona pule przykladowych
# podmiotow), nie wymaga rejestracji. Zweryfikowany dzialajacy na zywo
# 2026-07-14 (patrz podsumowanie w rozmowie).
KLUCZ_TESTOWY_GUS = "abcde12345abcde12345"


def _katalog_konfiguracji() -> Path:
    if os.name == "nt":
        podstawa = os.environ.get("APPDATA") or str(Path.home())
    else:
        podstawa = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(podstawa) / NAZWA_KATALOGU


def _plik_ustawien() -> Path:
    return _katalog_konfiguracji() / NAZWA_PLIKU


def _wczytaj() -> dict:
    plik = _plik_ustawien()
    if not plik.exists():
        return {}
    try:
        dane = json.loads(plik.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return dane if isinstance(dane, dict) else {}


def _zapisz(dane: dict) -> None:
    katalog = _katalog_konfiguracji()
    katalog.mkdir(parents=True, exist_ok=True)
    _plik_ustawien().write_text(json.dumps(dane), encoding="utf-8")


def wczytaj_ustawienia_gus() -> dict:
    """Zwraca stan do wyswietlenia w UI - NIGDY surowego klucza (analogicznie
    do hasla appki: mozna nadpisac, nie mozna odczytac z powrotem)."""
    dane = _wczytaj()
    return {
        "srodowisko": dane.get("gus_srodowisko", DOMYSLNE_SRODOWISKO_GUS),
        "ma_klucz_produkcyjny": bool(dane.get("gus_klucz_produkcyjny")),
    }


def pobierz_dane_polaczenia_gus() -> tuple[str, str]:
    """Zwraca (klucz, srodowisko) faktycznie uzywane do wywolania SOAP.

    Jesli uzytkownik wybral produkcyjne, ale nie ma jeszcze zapisanego klucza
    (typowy stan zaraz po Fazie 14, zanim klucz przyjdzie z GUS), appka NIE
    ma sie wywalac - spada z powrotem na srodowisko testowe z kluczem
    testowym, zeby funkcja zostala uzywalna od razu.
    """
    dane = _wczytaj()
    srodowisko = dane.get("gus_srodowisko", DOMYSLNE_SRODOWISKO_GUS)
    klucz_produkcyjny = dane.get("gus_klucz_produkcyjny")
    if srodowisko == "produkcyjne" and klucz_produkcyjny:
        return klucz_produkcyjny, "produkcyjne"
    return KLUCZ_TESTOWY_GUS, "testowe"


def zapisz_ustawienia_gus(zmiany: dict) -> dict:
    """`zmiany` moze zawierac 'srodowisko' i/lub 'klucz_produkcyjny' (te same
    nazwy pol co w schemacie API UstawieniaGusIn - tlumaczenie na nazwy
    kluczy w pliku ('gus_...') dzieje sie tutaj). 'klucz_produkcyjny'
    ustawiony na pusty/None czysci zapisany klucz. Zwraca stan jak
    wczytaj_ustawienia_gus()."""
    if "srodowisko" in zmiany and zmiany["srodowisko"] not in SRODOWISKA_GUS:
        raise ValueError(f"Nieznane środowisko GUS: {zmiany['srodowisko']}")

    dane = _wczytaj()
    if "srodowisko" in zmiany:
        dane["gus_srodowisko"] = zmiany["srodowisko"]
    if "klucz_produkcyjny" in zmiany:
        if zmiany["klucz_produkcyjny"]:
            dane["gus_klucz_produkcyjny"] = zmiany["klucz_produkcyjny"]
        else:
            dane.pop("gus_klucz_produkcyjny", None)
    _zapisz(dane)
    return wczytaj_ustawienia_gus()
