import json
from pathlib import Path

import customtkinter as ctk

from app.profil import katalog_appdata_lokalny

# Ustawienia appki trzymane lokalnie poza baza i poza repozytorium. W
# odroznieniu od auth.json/ksef.json/ustawienia_profilu.json (per-profil,
# Faza 25 - patrz gui/nastawienia_profilu.py), ten plik zostaje
# GLOBALNY (wspolny dla wszystkich profili): tryb wygladu, geometria okna i
# zapamietane filtry/sortowania list to preferencje UI/monitora, nie dane
# firmy - ekran wyboru profilu (gui/windows/ekran_wyboru_profilu.py) tez
# potrzebuje trybu wygladu, zanim jakikolwiek profil zostanie wybrany.
NAZWA_PLIKU = "ustawienia.json"


def _katalog_konfiguracji() -> Path:
    return katalog_appdata_lokalny()

DOMYSLNY_TRYB = "system"

# Klucz PL (zapisywany w pliku i uzywany w UI) -> string oczekiwany przez
# ctk.set_appearance_mode.
TRYBY_WYGLADU_CTK: dict[str, str] = {
    "jasny": "Light",
    "ciemny": "Dark",
    "system": "System",
}

ETYKIETY_TRYBOW_WYGLADU: dict[str, str] = {
    "jasny": "Jasny",
    "ciemny": "Ciemny",
    "system": "Zgodnie z systemem",
}


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
    """Ogolny odczyt jednej wartosci z pliku ustawien (Faza 16C: filtry,
    sortowanie, geometria okna - ten sam plik co tryb wygladu z 16A)."""
    return _wczytaj_wszystko().get(klucz, domyslne)


def zapisz(klucz: str, wartosc) -> None:
    """Ogolny zapis jednej wartosci - laczy sie (merge) z reszta pliku, zeby
    zapis jednego ustawienia nie nadpisywal pozostalych."""
    dane = _wczytaj_wszystko()
    dane[klucz] = wartosc
    _zapisz_wszystko(dane)


def wczytaj_tryb_wygladu() -> str:
    tryb = wczytaj("tryb_wygladu")
    return tryb if tryb in TRYBY_WYGLADU_CTK else DOMYSLNY_TRYB


def zapisz_tryb_wygladu(tryb: str) -> None:
    if tryb not in TRYBY_WYGLADU_CTK:
        raise ValueError(f"Nieznany tryb wygladu: {tryb}")
    zapisz("tryb_wygladu", tryb)


def zastosuj_tryb_wygladu(tryb: str | None = None) -> str:
    """Wczytuje (jesli tryb=None) i aplikuje tryb wygladu przez ctk.set_appearance_mode.
    Bezpieczne wywolac przed utworzeniem jakiegokolwiek okna Tk. Zwraca zastosowany
    klucz PL, przydatne przy starcie appki do zainicjowania kontrolki w Ustawieniach."""
    tryb = tryb if tryb in TRYBY_WYGLADU_CTK else wczytaj_tryb_wygladu()
    ctk.set_appearance_mode(TRYBY_WYGLADU_CTK[tryb])
    return tryb
