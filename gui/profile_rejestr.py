"""Rejestr profili firm (Faza 25) - lista wszystkich firm skonfigurowanych na
tym komputerze, %LOCALAPPDATA%/FakturyPro/profiles.json. Czysto lokalny plik,
zero polaczenia z baza danych - musi byc czytelny PRZED wyborem/uruchomieniem
jakiejkolwiek bazy profilu (patrz gui/windows/ekran_wyboru_profilu.py, ktore
dziala jeszcze przed startem prywatnego Postgresa).

`nazwa_bazy` jest zapisywana JAWNIE per-profil (nie wyprowadzana za kazdym
razem z konwencji `faktury_pro_<id>`), zeby profil zmigrowany ze starej,
jednofirmowej instalacji (gui/migracja_profili.py) mogl zachowac swoja
oryginalna nazwe bazy `faktury_pro` bez zadnego rename bazy danych.
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.profil import katalog_appdata_lokalny

NAZWA_PLIKU = "profiles.json"
PREFIKS_NAZWY_BAZY = "faktury_pro_"


@dataclass
class Profil:
    id: str
    nazwa_bazy: str
    nazwa_wyswietlana: str | None
    utworzono: str
    ostatnio_uzywany: str | None


def _plik_rejestru() -> Path:
    return katalog_appdata_lokalny() / NAZWA_PLIKU


def plik_rejestru_istnieje() -> bool:
    return _plik_rejestru().exists()


def _wczytaj_surowe() -> list[dict]:
    plik = _plik_rejestru()
    if not plik.exists():
        return []
    try:
        dane = json.loads(plik.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return dane.get("profile", []) if isinstance(dane, dict) else []


def _zapisz_surowe(profile: list[dict]) -> None:
    katalog = katalog_appdata_lokalny()
    katalog.mkdir(parents=True, exist_ok=True)
    _plik_rejestru().write_text(
        json.dumps({"wersja": 1, "profile": profile}, indent=2), encoding="utf-8"
    )


def wczytaj_wszystkie() -> list[Profil]:
    """Posortowane: ostatnio uzywane pierwsze (najnowsze na gorze), profile
    nigdy nieuzyte na koncu (w kolejnosci utworzenia)."""
    profile = [Profil(**p) for p in _wczytaj_surowe()]
    uzywane = sorted(
        (p for p in profile if p.ostatnio_uzywany is not None),
        key=lambda p: p.ostatnio_uzywany,
        reverse=True,
    )
    nieuzywane = sorted(
        (p for p in profile if p.ostatnio_uzywany is None),
        key=lambda p: p.utworzono,
    )
    return uzywane + nieuzywane


def pobierz(profil_id: str) -> Profil | None:
    for p in wczytaj_wszystkie():
        if p.id == profil_id:
            return p
    return None


def utworz_nowy_profil() -> Profil:
    """Generuje nowe id (UUID4 hex) i konwencje nazwy bazy `faktury_pro_<id>` -
    JEDYNE miejsce w appce, gdzie ta konwencja jest zakodowana. NIE tworzy
    jeszcze samej bazy PostgreSQL ani katalogu danych - baza powstaje
    naturalnie przy starcie backendu (gui/postgres_serwer.py:
    upewnij_baze_i_migracje, bez zmian w tej funkcji), po tym jak
    gui/main.py ustawi ten profil jako aktywny."""
    nowy_id = uuid.uuid4().hex
    teraz = datetime.now(timezone.utc).isoformat()
    wpis = Profil(
        id=nowy_id,
        nazwa_bazy=f"{PREFIKS_NAZWY_BAZY}{nowy_id}",
        nazwa_wyswietlana=None,
        utworzono=teraz,
        ostatnio_uzywany=None,
    )
    surowe = _wczytaj_surowe()
    surowe.append(asdict(wpis))
    _zapisz_surowe(surowe)
    return wpis


def dodaj_zmigrowany(profil_id: str, nazwa_bazy: str) -> Profil:
    """Uzywane WYLACZNIE przez gui/migracja_profili.py - IDEMPOTENTNE (jesli
    wpis o tym id juz istnieje, nic nie robi zamiast dodawac duplikat, zeby
    przerwana w polowie migracja bezpiecznie wznowila sie przy kolejnym
    starcie)."""
    istniejacy = pobierz(profil_id)
    if istniejacy is not None:
        return istniejacy
    teraz = datetime.now(timezone.utc).isoformat()
    wpis = Profil(profil_id, nazwa_bazy, None, teraz, None)
    surowe = _wczytaj_surowe()
    surowe.append(asdict(wpis))
    _zapisz_surowe(surowe)
    return wpis


def ustaw_nazwe(profil_id: str, nazwa: str) -> None:
    surowe = _wczytaj_surowe()
    for p in surowe:
        if p["id"] == profil_id:
            p["nazwa_wyswietlana"] = nazwa
    _zapisz_surowe(surowe)


def oznacz_uzyty(profil_id: str) -> None:
    surowe = _wczytaj_surowe()
    for p in surowe:
        if p["id"] == profil_id:
            p["ostatnio_uzywany"] = datetime.now(timezone.utc).isoformat()
    _zapisz_surowe(surowe)


def usun(profil_id: str) -> None:
    surowe = [p for p in _wczytaj_surowe() if p["id"] != profil_id]
    _zapisz_surowe(surowe)
