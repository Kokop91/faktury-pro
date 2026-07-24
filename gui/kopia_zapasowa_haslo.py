"""Bezpieczne przechowywanie hasla szyfrowania AUTOMATYCZNYCH kopii zapasowych
(rozszerzenie Fazy 22) - WYLACZNIE dla trybu "Wykonuj kopie automatycznie" w
gui/windows/widok_ustawien.py. Tryb domyslny ("Pytaj mnie za kazdym razem")
NADAL nigdzie nie zapisuje hasla, dokladnie jak opisano w gui/kopia_zapasowa.py.

SWIADOMY KOMPROMIS bezpieczenstwa: gui/kopia_zapasowa.py celowo NIGDY nie
zapisywalo hasla kopii, zeby kopia dala sie odszyfrowac takze po awarii TEGO
komputera (nowy sprzet/konto Windows). Automatyczny tryb bez pytania wymaga
jednak hasla przy KAZDYM wykonaniu bez udzialu uzytkownika - jedyny sposob to
zapisac je lokalnie. Uzytkownik podaje je RAZ, wlaczajac tryb automatyczny, a
appka zapisuje je zaszyfrowane Windows DPAPI (ten sam mechanizm co token KSeF,
app/services/ksef_ustawienia.py) - odszyfrowanie mozliwe tylko na tym samym
koncie Windows na tym samym komputerze. UI (widok_ustawien.py) jasno tlumaczy
ten kompromis PRZED wlaczeniem trybu automatycznego."""
import base64
import json
import os
from pathlib import Path

NAZWA_PLIKU = "backup_haslo.json"

# Patrz app/services/ksef_ustawienia.py:_ENTROPIA po wyjasnienie roli tej
# wartosci w DPAPI - inna niz tam, zeby zaszyfrowany blob hasla backupu nie
# dal sie odszyfrowac przy uzyciu entropii tokena KSeF (i odwrotnie).
_ENTROPIA = b"faktury-pro-backup-haslo-v1"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


def _katalog_konfiguracji() -> Path:
    from app.profil import katalog_aktywnego_profilu

    return katalog_aktywnego_profilu()


def _plik() -> Path:
    return _katalog_konfiguracji() / NAZWA_PLIKU


def _szyfruj(tekst: str) -> str:
    if os.name != "nt":
        raise RuntimeError(
            "Bezpieczne przechowywanie hasła kopii zapasowej wymaga systemu Windows (DPAPI)."
        )
    import win32crypt

    zaszyfrowane = win32crypt.CryptProtectData(
        tekst.encode("utf-8"),
        "FakturyPro Backup",
        _ENTROPIA,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
    )
    return base64.b64encode(zaszyfrowane).decode("ascii")


def _odszyfruj(tekst_b64: str) -> str:
    if os.name != "nt":
        raise RuntimeError(
            "Bezpieczne przechowywanie hasła kopii zapasowej wymaga systemu Windows (DPAPI)."
        )
    import win32crypt

    surowe = base64.b64decode(tekst_b64)
    _opis, odszyfrowane = win32crypt.CryptUnprotectData(
        surowe, _ENTROPIA, None, None, _CRYPTPROTECT_UI_FORBIDDEN
    )
    return odszyfrowane.decode("utf-8")


def czy_zapisane() -> bool:
    return _plik().exists()


def zapisz_haslo(haslo: str) -> None:
    katalog = _katalog_konfiguracji()
    katalog.mkdir(parents=True, exist_ok=True)
    _plik().write_text(
        json.dumps({"haslo_zaszyfrowane": _szyfruj(haslo)}), encoding="utf-8"
    )


def wczytaj_haslo() -> str | None:
    """None jesli haslo nie zostalo jeszcze zapisane ALBO nie da sie go
    odszyfrowac (np. plik przeniesiony na inny komputer/konto - DPAPI wiaze
    szyfrowanie z kontem Windows). Wywolujacy (kopia_zapasowa.py) traktuje to
    jak brak hasla - automatyczny backup wtedy nie moze sie wykonac."""
    plik = _plik()
    if not plik.exists():
        return None
    try:
        dane = json.loads(plik.read_text(encoding="utf-8"))
        return _odszyfruj(dane["haslo_zaszyfrowane"])
    except Exception:
        return None


def usun_haslo() -> None:
    plik = _plik()
    if plik.exists():
        plik.unlink()
