"""Ustawienia PER-PROFILU (Faza 25) - w odroznieniu od gui/nastawienia.py
(globalne: tryb wygladu, geometria okna, filtry/sortowania list), ten plik
trzyma ustawienia zwiazane z konkretna firma: obecnie wylacznie katalog
docelowy kopii zapasowej i data ostatniego udanego backupu
(gui/kopia_zapasowa.py). Zyje w katalogu aktywnego profilu
(app/profil.py:katalog_aktywnego_profilu), pod NAZWA_PLIKU rozna od
globalnego "ustawienia.json", zeby nie bylo watpliwosci przy przegladaniu
katalogu profilu, ktory plik jest ktory.

Mechanizm wczytaj/zapisz jest celowo niemal identyczny z gui/nastawienia.py -
dwa osobne, male pliki sa prostsze niz jeden wspolny model z flaga
globalny/per-profil na kazdym kluczu.
"""

import json
from pathlib import Path

from app.profil import katalog_aktywnego_profilu

NAZWA_PLIKU = "ustawienia_profilu.json"


def _katalog_konfiguracji() -> Path:
    return katalog_aktywnego_profilu()


def _plik_ustawien() -> Path:
    return _katalog_konfiguracji() / NAZWA_PLIKU


def _wczytaj_wszystko() -> dict:
    plik = _plik_ustawien()
    if not plik.exists():
        return {}
    try:
        dane = json.loads(plik.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return dane if isinstance(dane, dict) else {}


def _zapisz_wszystko(dane: dict) -> None:
    katalog = _katalog_konfiguracji()
    katalog.mkdir(parents=True, exist_ok=True)
    _plik_ustawien().write_text(json.dumps(dane), encoding="utf-8")


def wczytaj(klucz: str, domyslne=None):
    return _wczytaj_wszystko().get(klucz, domyslne)


def zapisz(klucz: str, wartosc) -> None:
    dane = _wczytaj_wszystko()
    dane[klucz] = wartosc
    _zapisz_wszystko(dane)
