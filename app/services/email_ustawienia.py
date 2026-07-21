"""Ustawienia SMTP (Faza 23, Etap 4) - appka NIE MIALA zadnej infrastruktury
wysylki e-mail mimo ze byla zaplanowana w PLAN_PROJEKTU.md dla Etapu 1 (nigdy
nie zaimplementowana - zweryfikowane wprost w kodzie przed ta faza, nie
zgadywane). Ten plik jest fundamentem: przypomnienia o platnosciach (Faza 23)
sa PIERWSZYM uzyciem tej infrastruktury, ale sam mechanizm jest ogolny.

Wzorzec identyczny jak token KSeF (Faza 12A, app/services/ksef_ustawienia.py):
haslo SMTP musi byc ODCZYTYWALNE (appka loguje sie nim do serwera pocztowego
przy kazdej wysylce), wiec nie moze byc jednokierunkowym hashem jak haslo
appki (bcrypt) - jest zaszyfrowane odwracalnie przez Windows DPAPI, co
oznacza, ze dziala TYLKO na tym samym koncie Windows na tym samym komputerze
(w odroznieniu np. od hasla szyfrowania kopii zapasowej z Fazy 22, ktore
swiadomie NIGDZIE nie jest zapisywane, bo musi przetrwac awarie komputera)."""
import base64
import json
import os
from pathlib import Path

from app.profil import katalog_aktywnego_profilu

# Ustawienia SMTP sa daną PER-PROFILU (Faza 25) - kazda firma ma wlasna
# skrzynke nadawcza, zyja w katalogu aktywnego profilu (app/profil.py:
# katalog_aktywnego_profilu).
NAZWA_PLIKU = "email.json"

DOMYSLNY_PORT = 587
DOMYSLNE_SZYFROWANIE = "starttls"
SPOSOBY_SZYFROWANIA = ("starttls", "ssl", "brak")

_ENTROPIA = b"faktury-pro-smtp-haslo-v1"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


def _katalog_konfiguracji() -> Path:
    return katalog_aktywnego_profilu()


def _plik_ustawien() -> Path:
    return _katalog_konfiguracji() / NAZWA_PLIKU


def _szyfruj(tekst: str) -> str:
    if os.name != "nt":
        raise RuntimeError(
            "Bezpieczne przechowywanie hasła SMTP wymaga systemu Windows (DPAPI)."
        )
    import win32crypt

    zaszyfrowane = win32crypt.CryptProtectData(
        tekst.encode("utf-8"), "FakturyPro SMTP", _ENTROPIA, None, None, _CRYPTPROTECT_UI_FORBIDDEN
    )
    return base64.b64encode(zaszyfrowane).decode("ascii")


def _odszyfruj(tekst_b64: str) -> str:
    if os.name != "nt":
        raise RuntimeError(
            "Bezpieczne przechowywanie hasła SMTP wymaga systemu Windows (DPAPI)."
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


def wczytaj_ustawienia_email() -> dict:
    """Zwraca stan do wyswietlenia w UI - NIGDY surowego hasla (ten sam wzorzec
    maskowania co token KSeF/klucz produkcyjny GUS)."""
    dane = _wczytaj()
    return {
        "host": dane.get("email_host"),
        "port": dane.get("email_port", DOMYSLNY_PORT),
        "uzytkownik": dane.get("email_uzytkownik"),
        "ma_haslo": bool(dane.get("email_haslo_zaszyfrowane")),
        "szyfrowanie": dane.get("email_szyfrowanie", DOMYSLNE_SZYFROWANIE),
        "nadawca_adres": dane.get("email_nadawca_adres"),
        "nadawca_nazwa": dane.get("email_nadawca_nazwa"),
    }


def pobierz_dane_polaczenia_email() -> dict | None:
    """Zwraca dane faktycznie uzywane do wysylki (z odszyfrowanym haslem), albo
    None, jesli SMTP nie jest jeszcze skonfigurowany albo haslo nie da sie
    odszyfrowac (np. plik przeniesiony na inny komputer/konto)."""
    dane = _wczytaj()
    haslo_zaszyfrowane = dane.get("email_haslo_zaszyfrowane")
    if not (dane.get("email_host") and dane.get("email_uzytkownik") and haslo_zaszyfrowane):
        return None
    try:
        haslo = _odszyfruj(haslo_zaszyfrowane)
    except Exception:
        return None
    return {
        "host": dane["email_host"],
        "port": dane.get("email_port", DOMYSLNY_PORT),
        "uzytkownik": dane["email_uzytkownik"],
        "haslo": haslo,
        "szyfrowanie": dane.get("email_szyfrowanie", DOMYSLNE_SZYFROWANIE),
        "nadawca_adres": dane.get("email_nadawca_adres") or dane["email_uzytkownik"],
        "nadawca_nazwa": dane.get("email_nadawca_nazwa"),
    }


def zapisz_ustawienia_email(zmiany: dict) -> dict:
    """`zmiany` moze zawierac 'host', 'port', 'uzytkownik', 'haslo', 'szyfrowanie',
    'nadawca_adres', 'nadawca_nazwa' (te same nazwy pol co UstawieniaEmailIn).
    'haslo' ustawione na pusty/None NIE czysci zapisanego hasla (w odroznieniu
    od tokena KSeF) - w formularzu SMTP puste pole hasla zawsze oznacza
    "zostaw bez zmian", bo appka jest bezuzyteczna bez zapisanego hasla i nie
    ma tu odpowiednika "wylacz integracje" jak przy KSeF. Zwraca stan jak
    wczytaj_ustawienia_email()."""
    if "szyfrowanie" in zmiany and zmiany["szyfrowanie"] not in SPOSOBY_SZYFROWANIA:
        raise ValueError(f"Nieznany sposób szyfrowania SMTP: {zmiany['szyfrowanie']}")

    dane = _wczytaj()
    if "host" in zmiany:
        dane["email_host"] = zmiany["host"]
    if "port" in zmiany and zmiany["port"] is not None:
        dane["email_port"] = int(zmiany["port"])
    if "uzytkownik" in zmiany:
        dane["email_uzytkownik"] = zmiany["uzytkownik"]
    if zmiany.get("haslo"):
        dane["email_haslo_zaszyfrowane"] = _szyfruj(zmiany["haslo"])
    if "szyfrowanie" in zmiany:
        dane["email_szyfrowanie"] = zmiany["szyfrowanie"]
    if "nadawca_adres" in zmiany:
        dane["email_nadawca_adres"] = zmiany["nadawca_adres"]
    if "nadawca_nazwa" in zmiany:
        dane["email_nadawca_nazwa"] = zmiany["nadawca_nazwa"]
    _zapisz(dane)
    return wczytaj_ustawienia_email()
