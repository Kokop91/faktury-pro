"""Swiadomosc wersji i prosty, RECZNY proces dostarczania poprawek - NIE
pelny auto-update (appka nigdy sama nic nie pobiera ani nie instaluje,
wylacznie informuje uzytkownika, ze nowsza wersja istnieje, i gdzie ja moze
pobrac recznie, tak jak przy pierwszej instalacji).

Mechanizm sprawdzania: appka pobiera POJEDYNCZA LINIE TEKSTU (numer wersji,
nic wiecej) z pliku wersja_aktualna.txt w korzeniu tego repozytorium na
GitHub, przez publiczny "raw" URL - NIE wymaga zadnego API/backendu poza
samym GitHubem, ktory kamil (developer) moze zaktualizowac zwyklym
zatwierdzeniem zmiany w pliku (patrz CLAUDE.md, sekcja "Wersjonowanie i
aktualizacje", po dokladna instrukcje publikowania nowej wersji).

Odpornosc na brak internetu (patrz przeglad odpornosci appki na problemy
sieciowe): to funkcja czysto informacyjna, wiec jej niepowodzenie NIGDY nie
moze przeszkodzic w normalnym dzialaniu appki - blad sieciowy jest lapany i
zwracany jako czytelny polski komunikat (HTTPException 502), dokladnie tak
samo jak przy NBP/GUS/bialej liscie, NIE jako niezlapany wyjatek.
"""

import re

import requests
from fastapi import HTTPException, status

from app.wersja import WERSJA

URL_WERSJI = "https://raw.githubusercontent.com/Kokop91/faktury-pro/main/wersja_aktualna.txt"
URL_POBIERANIA = "https://github.com/Kokop91/faktury-pro/releases"
TIMEOUT_S = 5.0

_WZORZEC_WERSJI = re.compile(r"^\d+\.\d+\.\d+$")


def _rozbij_wersje(wersja: str) -> tuple[int, int, int]:
    a, b, c = wersja.split(".")
    return (int(a), int(b), int(c))


def sprawdz_dostepna_aktualizacje() -> dict:
    """Zwraca slownik z biezaca/najnowsza wersja i flaga, czy dostepna jest
    nowsza. Rzuca HTTPException 502 z czytelnym polskim komunikatem przy
    problemie sieciowym albo nieoczekiwanej zawartosci pliku - appka NIGDY
    nie ma sie z tego powodu wywalic, tylko pokazac blad w Ustawieniach."""
    try:
        odpowiedz = requests.get(URL_WERSJI, timeout=TIMEOUT_S)
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Nie udało się sprawdzić dostępności aktualizacji: {e}",
        ) from e

    if odpowiedz.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Serwis aktualizacji zwrócił błąd (HTTP {odpowiedz.status_code}).",
        )

    tekst = odpowiedz.text.strip()
    if not _WZORZEC_WERSJI.match(tekst):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Serwis aktualizacji zwrócił nieoczekiwaną odpowiedź.",
        )

    return {
        "wersja_biezaca": WERSJA,
        "wersja_najnowsza": tekst,
        "dostepna_nowsza_wersja": _rozbij_wersje(tekst) > _rozbij_wersje(WERSJA),
        "url_pobierania": URL_POBIERANIA,
    }
