import base64
import json
import os
from datetime import datetime, timezone
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
    do klucza produkcyjnego GUS: mozna nadpisac, nie mozna odczytac z powrotem).
    `token_podglad` to WYLACZNIE ostatnie 4 znaki tokena (jak maskowanie numeru
    karty platniczej) - trzymane jawnie obok zaszyfrowanej wersji, tylko zeby
    uzytkownik mogl potwierdzic "tak, to ten token", bez ujawniania calosci."""
    dane = _wczytaj()
    return {
        "srodowisko": dane.get("ksef_srodowisko", DOMYSLNE_SRODOWISKO),
        "ma_token": bool(dane.get("ksef_token_zaszyfrowany")),
        "token_podglad": dane.get("ksef_token_podglad"),
        "sprawdzaj_koszty_przy_starcie": bool(dane.get("ksef_sprawdzaj_koszty_przy_starcie", False)),
        "ostatnie_sprawdzenie_kosztow": dane.get("ksef_ostatnie_sprawdzenie_kosztow"),
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
    """`zmiany` moze zawierac 'srodowisko', 'token' i/lub
    'sprawdzaj_koszty_przy_starcie' (te same nazwy pol co w schemacie API
    UstawieniaKsefIn). 'token' ustawiony na pusty/None czysci zapisany token.
    Zwraca stan jak wczytaj_ustawienia_ksef()."""
    if "srodowisko" in zmiany and zmiany["srodowisko"] not in SRODOWISKA:
        raise ValueError(f"Nieznane środowisko KSeF: {zmiany['srodowisko']}")

    dane = _wczytaj()
    if "srodowisko" in zmiany:
        dane["ksef_srodowisko"] = zmiany["srodowisko"]
    if "token" in zmiany:
        if zmiany["token"]:
            dane["ksef_token_zaszyfrowany"] = _szyfruj(zmiany["token"])
            dane["ksef_token_podglad"] = zmiany["token"][-4:]
        else:
            dane.pop("ksef_token_zaszyfrowany", None)
            dane.pop("ksef_token_podglad", None)
    if "sprawdzaj_koszty_przy_starcie" in zmiany:
        dane["ksef_sprawdzaj_koszty_przy_starcie"] = bool(zmiany["sprawdzaj_koszty_przy_starcie"])
    _zapisz(dane)
    return wczytaj_ustawienia_ksef()


def zapisz_ostatnie_sprawdzenie_kosztow() -> None:
    """Wolane po kazdym (udanym) sprawdzeniu KSeF pod katem nowych faktur
    kosztowych (patrz ksef_koszty_service.py) - NIEZALEZNE od tego, czy
    cokolwiek nowego znaleziono. To zwykla data "ostatniej proby", nie to samo
    co punkt startowy kolejnego okna (ten wyznacza MAX(data_trwalego_zapisu)
    juz pobranych dokumentow - bez znalezionych dokumentow ten punkt by sie
    nie przesunal, a uzytkownik i tak chce widziec, ze appka w ogole sprawdzala)."""
    dane = _wczytaj()
    dane["ksef_ostatnie_sprawdzenie_kosztow"] = datetime.now(timezone.utc).isoformat()
    _zapisz(dane)
