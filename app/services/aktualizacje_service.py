"""Swiadomosc wersji i wygodny, ale wciaz RECZNY proces dostarczania poprawek
(Faza 28) - appka NIGDY sama nie podmienia wlasnych plikow (to Poziom 3,
swiadomie odlozony na przyszlosc). Appka moze teraz POBRAC gotowy instalator
i go URUCHOMIC (patrz gui/aktualizacje.py), ale sama podmiana plikow programu
nadal nalezy WYLACZNIE do istniejacego, sprawdzonego instalatora Inno Setup
(installer.iss) - dokladnie tego samego, ktorego uzytkownik uruchomilby
recznie po pobraniu ze strony.

Mechanizm sprawdzania: appka pobiera plik wersja_aktualna.json w korzeniu
tego repozytorium na GitHub, przez publiczny "raw" URL - NIE wymaga zadnego
API/backendu poza samym GitHubem, ktory kamil (developer) moze zaktualizowac
zwyklym zatwierdzeniem zmiany w pliku (patrz CLAUDE.md, sekcja
"Wersjonowanie i aktualizacje", i CHECKLIST_WYDANIA.md, po dokladna
instrukcje publikowania nowej wersji).

Format JSON (nie plaski tekst jak przed Faza 28) - swiadomy wybor: appka
potrzebuje teraz TRZECH niezaleznych informacji (numer wersji, bezposredni
URL do pliku instalatora, wieloliniowy changelog), a plaski format
"linia = pole" wymagalby wlasnego, kruchego schematu escapowania nowych linii
w changelogu. JSON to obsluguje z pudelka, jest jednoznaczny do parsowania i
latwo rozszerzalny o kolejne pola w przyszlosci bez zmiany formatu.

WSTECZNA ZGODNOSC: stary, plaski wersja_aktualna.txt (SAM numer wersji, nic
wiecej) zostaje NIETKNIETY w repozytorium i nadal aktualizowany przy kazdym
wydaniu (patrz CHECKLIST_WYDANIA.md) - appki w wersji sprzed Fazy 28 (<=1.1.1)
nadal go czytaja i nie przestana dzialac. Ten modul (juz od Fazy 28) czyta
WYLACZNIE nowy .json - nie ma logiki "sprobuj JSON, potem spadnij na txt",
bo od tej fazy w gore .json bedzie publikowany przy KAZDYM wydaniu razem z
.txt (jedno dodatkowe zatwierdzenie pliku w checklist wydania, nie osobny
proces) - nie ma wiec scenariusza, w ktorym appka >=1.1.1+Faza28 sprawdza
aktualizacje, a .json jeszcze nie istnieje.

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

URL_WERSJI_JSON = "https://raw.githubusercontent.com/Kokop91/faktury-pro/main/wersja_aktualna.json"
URL_POBIERANIA = "https://github.com/Kokop91/faktury-pro/releases"
TIMEOUT_S = 5.0

_WZORZEC_WERSJI = re.compile(r"^\d+\.\d+\.\d+$")


def _rozbij_wersje(wersja: str) -> tuple[int, int, int]:
    a, b, c = wersja.split(".")
    return (int(a), int(b), int(c))


def sprawdz_dostepna_aktualizacje() -> dict:
    """Zwraca slownik z biezaca/najnowsza wersja, URL-em instalatora, opisem
    zmian i flaga, czy dostepna jest nowsza wersja. Rzuca HTTPException 502 z
    czytelnym polskim komunikatem przy problemie sieciowym albo
    nieoczekiwanej/niekompletnej zawartosci pliku - appka NIGDY nie ma sie z
    tego powodu wywalic, tylko pokazac blad w Ustawieniach."""
    try:
        odpowiedz = requests.get(URL_WERSJI_JSON, timeout=TIMEOUT_S)
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

    try:
        dane = odpowiedz.json()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Serwis aktualizacji zwrócił nieoczekiwaną odpowiedź.",
        ) from e

    wersja_najnowsza = str(dane.get("wersja", "")).strip()
    url_instalatora = str(dane.get("url_instalatora", "")).strip()
    zmiany = str(dane.get("zmiany", "")).strip()

    if not _WZORZEC_WERSJI.match(wersja_najnowsza) or not url_instalatora:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Serwis aktualizacji zwrócił niekompletną odpowiedź.",
        )

    return {
        "wersja_biezaca": WERSJA,
        "wersja_najnowsza": wersja_najnowsza,
        "dostepna_nowsza_wersja": _rozbij_wersje(wersja_najnowsza) > _rozbij_wersje(WERSJA),
        "url_pobierania": URL_POBIERANIA,
        "url_instalatora": url_instalatora,
        "zmiany": zmiany,
    }
