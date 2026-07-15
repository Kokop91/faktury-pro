import base64
import json
import os
from pathlib import Path

# Ustawienia integracji KSeF (Faza 12A) trzymane lokalnie poza baza danych i
# poza repozytorium - ten sam katalog co haslo appki (gui/auth.py) i ustawienia
# GUS (integracje_ustawienia.py), ale WLASNY plik: token KSeF jest sekretem
# innego rodzaju niz haslo appki - appka musi go moc ODCZYTAC (wysyla go do
# KSeF przy kazdym uwierzytelnieniu), wiec nie moze byc jednokierunkowym
# hashem jak bcrypt. Jest zaszyfrowany odwracalnie przez Windows DPAPI
# (CryptProtectData/CryptUnprotectData) - odszyfrowanie jest mozliwe tylko
# na tym samym koncie Windows na tym samym komputerze (ten sam mechanizm,
# ktorego np. Chrome uzywa do zapisanych hasel).
NAZWA_KATALOGU = "FakturyPro"
NAZWA_PLIKU = "ksef.json"

DOMYSLNE_SRODOWISKO = "testowe"
SRODOWISKA = ("testowe", "produkcyjne")

# Wartosc "OptionalEntropy" DPAPI - dodatkowy skladnik szyfrowania obok
# tajemnicy zwiazanej z kontem Windows. Nie jest to sekret sam w sobie (moze
# byc jawny w kodzie), tylko usztywnienie, zeby ten sam zaszyfrowany blob nie
# dal sie odszyfrowac innym wywolaniem CryptUnprotectData bez podania tej
# samej wartosci.
_ENTROPIA = b"faktury-pro-ksef-token-v1"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


def _katalog_konfiguracji() -> Path:
    if os.name == "nt":
        podstawa = os.environ.get("APPDATA") or str(Path.home())
    else:
        podstawa = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(podstawa) / NAZWA_KATALOGU


def _plik_ustawien() -> Path:
    return _katalog_konfiguracji() / NAZWA_PLIKU


def _szyfruj(tekst: str) -> str:
    if os.name != "nt":
        raise RuntimeError(
            "Bezpieczne przechowywanie tokena KSeF wymaga systemu Windows (DPAPI)."
        )
    import win32crypt

    zaszyfrowane = win32crypt.CryptProtectData(
        tekst.encode("utf-8"),
        "FakturyPro KSeF",
        _ENTROPIA,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
    )
    return base64.b64encode(zaszyfrowane).decode("ascii")


def _odszyfruj(tekst_b64: str) -> str:
    if os.name != "nt":
        raise RuntimeError(
            "Bezpieczne przechowywanie tokena KSeF wymaga systemu Windows (DPAPI)."
        )
    import win32crypt

    surowe = base64.b64decode(tekst_b64)
    _opis, odszyfrowane = win32crypt.CryptUnprotectData(
        surowe, _ENTROPIA, None, None, _CRYPTPROTECT_UI_FORBIDDEN
    )
    return odszyfrowane.decode("utf-8")


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


def wczytaj_ustawienia_ksef() -> dict:
    """Zwraca stan do wyswietlenia w UI - NIGDY surowego tokena (analogicznie
    do klucza produkcyjnego GUS: mozna nadpisac, nie mozna odczytac z powrotem)."""
    dane = _wczytaj()
    return {
        "srodowisko": dane.get("ksef_srodowisko", DOMYSLNE_SRODOWISKO),
        "ma_token": bool(dane.get("ksef_token_zaszyfrowany")),
    }


def pobierz_dane_polaczenia_ksef() -> tuple[str | None, str]:
    """Zwraca (token_odszyfrowany, srodowisko) faktycznie uzywane do
    uwierzytelnienia w KSeF. Token jest None, jesli nie zostal jeszcze
    zapisany albo nie da sie go odszyfrowac (np. plik przeniesiony na inny
    komputer/konto - DPAPI wiaze szyfrowanie z kontem Windows)."""
    dane = _wczytaj()
    srodowisko = dane.get("ksef_srodowisko", DOMYSLNE_SRODOWISKO)
    token_zaszyfrowany = dane.get("ksef_token_zaszyfrowany")
    if not token_zaszyfrowany:
        return None, srodowisko
    try:
        token = _odszyfruj(token_zaszyfrowany)
    except Exception:
        return None, srodowisko
    return token, srodowisko


def zapisz_ustawienia_ksef(zmiany: dict) -> dict:
    """`zmiany` moze zawierac 'srodowisko' i/lub 'token' (te same nazwy pol
    co w schemacie API UstawieniaKsefIn). 'token' ustawiony na pusty/None
    czysci zapisany token. Zwraca stan jak wczytaj_ustawienia_ksef()."""
    if "srodowisko" in zmiany and zmiany["srodowisko"] not in SRODOWISKA:
        raise ValueError(f"Nieznane środowisko KSeF: {zmiany['srodowisko']}")

    dane = _wczytaj()
    if "srodowisko" in zmiany:
        dane["ksef_srodowisko"] = zmiany["srodowisko"]
    if "token" in zmiany:
        if zmiany["token"]:
            dane["ksef_token_zaszyfrowany"] = _szyfruj(zmiany["token"])
        else:
            dane.pop("ksef_token_zaszyfrowany", None)
    _zapisz(dane)
    return wczytaj_ustawienia_ksef()
