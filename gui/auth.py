import json
from pathlib import Path

import bcrypt

from app.profil import katalog_aktywnego_profilu

# Kazdy profil firmy ma WLASNE, niezalezne haslo appki (Faza 25) - hash bcrypt
# zyje w katalogu aktywnego profilu (app/profil.py:katalog_aktywnego_profilu),
# CELOWO poza baza PostgreSQL (haslo do appki musi dzialac, zanim jakikolwiek
# serwer/baza w ogole wystartuje) i poza repozytorium (nigdy nie zyje w
# katalogu projektu, wiec nie ma ryzyka wrzucenia go do gita). W trybie
# deweloperskim (bez profili) spada na wspolny katalog globalny, dokladnie
# jak przed Faza 25.
NAZWA_PLIKU = "auth.json"


def _katalog_konfiguracji() -> Path:
    return katalog_aktywnego_profilu()


def _plik_auth() -> Path:
    return _katalog_konfiguracji() / NAZWA_PLIKU


def czy_haslo_ustawione() -> bool:
    return _plik_auth().exists()


def _wczytaj_hash() -> bytes | None:
    plik = _plik_auth()
    if not plik.exists():
        return None
    try:
        dane = json.loads(plik.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    hash_tekst = dane.get("hash_hasla")
    if not hash_tekst:
        return None
    return hash_tekst.encode("utf-8")


def ustaw_haslo(haslo: str) -> None:
    """Ustawia (lub nadpisuje, przy zmianie hasla) haslo appki."""
    hash_bajty = bcrypt.hashpw(haslo.encode("utf-8"), bcrypt.gensalt())
    katalog = _katalog_konfiguracji()
    katalog.mkdir(parents=True, exist_ok=True)
    _plik_auth().write_text(
        json.dumps({"hash_hasla": hash_bajty.decode("utf-8")}), encoding="utf-8"
    )


def zweryfikuj_haslo(haslo: str) -> bool:
    hash_bajty = _wczytaj_hash()
    if hash_bajty is None:
        return False
    try:
        return bcrypt.checkpw(haslo.encode("utf-8"), hash_bajty)
    except ValueError:
        # Uszkodzony/nieprawidlowy format hasha w pliku.
        return False
