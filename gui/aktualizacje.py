"""Pobieranie i uruchomienie instalatora aktualizacji (Faza 28) - rozszerza
dotychczasowy, czysto informacyjny mechanizm sprawdzania wersji
(app/services/aktualizacje_service.py) o wygodny krok "znajdz i pobierz
plik". CELOWO NIE jest to pelny auto-update (Poziom 3, swiadomie odlozony na
przyszlosc) - appka nadal NIGDY sama nie podmienia wlasnych plikow. Ten
modul robi wylacznie dwie rzeczy, ktore uzytkownik i tak zrobilby recznie:

1. Pobiera gotowy plik instalatora (.exe) z bezposredniego linku GitHub
   Release do WLASNEGO katalogu danych appki
   (%LOCALAPPDATA%/FakturyPro/aktualizacje/) - CELOWO NIE systemowego
   folderu Pobrane, zeby nie mieszac z innymi plikami uzytkownika i zeby
   appka mogla go pozniej sama, bez pytania o sciezke, odnalezc.
2. Uruchamia go jako zwykly, NIEZALEZNY proces (subprocess.Popen - appka go
   nie czeka ani dalej nie sledzi). Sama podmiana plikow programu nadal
   nalezy WYLACZNIE do istniejacego, sprawdzonego instalatora Inno Setup
   (installer.iss) - dokladnie tego samego, ktory uzytkownik uruchomilby
   recznie po pobraniu ze strony wydan.

Pobieranie idzie BEZPOSREDNIO z tego modulu (requests), z pominieciem
lokalnego backendu FastAPI - to czysto sieciowa operacja bez zwiazku z baza
danych/logika biznesowa appki, ten sam wzorzec co gui/kopia_zapasowa.py
(pg_dump/psql sa tez wywolywane bezposrednio z gui/, nie przez API).

Katalog docelowy jest GLOBALNY (katalog_appdata_lokalny), nie per-profil
(app/profil.py:katalog_profilu) - aktualizacja appki dotyczy WSZYSTKICH
profili firm naraz (to jeden, wspolny plik .exe programu), dokladnie jak
prywatny Postgres z Fazy 18B.

Wznawianie przerwanego pobierania: plik docelowy jest budowany pod nazwa
"<nazwa>.exe.czesciowy" i DOPIERO PO udanym zakonczeniu atomowo zmieniany
(os.replace) na koncowa nazwe "<nazwa>.exe" - sama obecnosc pliku BEZ tego
przyrostka jest wiec samowystarczalnym dowodem ukonczonego pobrania (nie
trzeba osobnego znacznika/flagi w innym pliku, ktora moglaby wyjsc z synchronizacji
z rzeczywistym stanem dysku). Kolejna proba pobrania TEJ SAMEJ wersji (np. po
przerwaniu przez utrate polaczenia, albo po prostu ponownym otwarciu
Ustawien) wysyla naglowek Range i doklada dalej do istniejacego pliku
".czesciowy" - GitHub Releases (serwowane przez objects.githubusercontent.com)
wspiera zakresowe pobieranie. Jesli serwer z jakiegos powodu Range
zignoruje (zwroci 200 zamiast 206), appka bezpiecznie zaczyna pobieranie
od nowa zamiast dopisac zle dane w losowym miejscu pliku.
"""

import os
import subprocess
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests

from app.profil import katalog_appdata_lokalny

TIMEOUT_POLACZENIE_S = 10.0
ROZMIAR_CHUNK_BAJTY = 256 * 1024
PRZYROSTEK_CZESCIOWY = ".czesciowy"

NazwaPostepu = Callable[[int, "int | None"], None]


class BladPobieraniaAktualizacji(Exception):
    pass


def _katalog_aktualizacji() -> Path:
    katalog = katalog_appdata_lokalny() / "aktualizacje"
    katalog.mkdir(parents=True, exist_ok=True)
    return katalog


def _nazwa_pliku_z_url(url: str) -> str:
    nazwa = Path(urlparse(url).path).name
    if not nazwa:
        raise BladPobieraniaAktualizacji("Nieprawidłowy adres pliku instalatora.")
    return nazwa


def plik_docelowy(url_instalatora: str) -> Path:
    return _katalog_aktualizacji() / _nazwa_pliku_z_url(url_instalatora)


def czy_juz_pobrany(url_instalatora: str) -> bool:
    """True, jesli instalator DOKLADNIE tej wersji (nazwa pliku z URL-a) jest
    juz w calosci na dysku - appka moze wtedy pominac ponowne pobieranie i
    przejsc prosto do stanu "Zainstaluj aktualizacje", nawet po zamknieciu i
    ponownym otwarciu Ustawien albo calej appki."""
    plik = plik_docelowy(url_instalatora)
    return plik.exists() and plik.stat().st_size > 0


def _posprzataj_stare_pliki(nazwa_biezaca: str) -> None:
    """Usuwa z katalogu aktualizacji WSZYSTKO poza plikami zwiazanymi z
    biezaco sprawdzana wersja (kompletny plik i/lub jego ".czesciowy") -
    porzucone pobrania starszych, juz nieaktualnych wersji (dokonczone albo
    przerwane w polowie) nie powinny zalegac bez konca. Niekrytyczne - blad
    usuniecia pojedynczego pliku nie przerywa biezacego pobierania."""
    katalog = _katalog_aktualizacji()
    zachowaj = {nazwa_biezaca, f"{nazwa_biezaca}{PRZYROSTEK_CZESCIOWY}"}
    for plik in katalog.iterdir():
        if plik.is_file() and plik.name not in zachowaj:
            try:
                plik.unlink()
            except OSError:
                pass


def pobierz_instalator(url_instalatora: str, na_postep: NazwaPostepu) -> Path:
    """Pobiera plik instalatora z obsluga wznowienia (Range). `na_postep`
    dostaje (pobrane_bajty, calkowity_rozmiar_bajty_lub_None) po kazdym
    kawalku - WOLANE Z WATKU W TLE, wolajacy odpowiada za bezpieczne
    przekazanie na watek Tk (ten sam wzorzec .after() co gui/watki.py i
    gui/windows/ekran_startu.py).

    Rzuca BladPobieraniaAktualizacji z czytelnym polskim komunikatem przy
    problemie sieciowym, bledzie serwera albo braku miejsca na dysku - NIGDY
    nie zostawia pliku docelowego (bez przyrostka .czesciowy) w niekompletnym
    stanie, wiec czy_juz_pobrany() zawsze mowi prawde o faktycznym stanie dysku.
    """
    nazwa = _nazwa_pliku_z_url(url_instalatora)
    _posprzataj_stare_pliki(nazwa)

    docelowy = _katalog_aktualizacji() / nazwa
    if docelowy.exists() and docelowy.stat().st_size > 0:
        return docelowy  # juz w pelni pobrany wczesniej (np. poprzednia sesja)

    czesciowy = docelowy.with_name(docelowy.name + PRZYROSTEK_CZESCIOWY)
    juz_pobrane_bajty = czesciowy.stat().st_size if czesciowy.exists() else 0
    naglowki = {"Range": f"bytes={juz_pobrane_bajty}-"} if juz_pobrane_bajty else {}

    try:
        odpowiedz = requests.get(
            url_instalatora, headers=naglowki, stream=True, timeout=TIMEOUT_POLACZENIE_S
        )
    except requests.exceptions.RequestException as e:
        raise BladPobieraniaAktualizacji(
            "Nie udało się połączyć z serwerem pobierania - sprawdź połączenie "
            f"z internetem ({e})."
        ) from e

    with odpowiedz:
        if juz_pobrane_bajty and odpowiedz.status_code == 416:
            # "Range Not Satisfiable" - czesciowy plik jest juz kompletny albo
            # uszkodzony (wiekszy niz cala zawartosc na serwerze); zaczynamy od zera.
            czesciowy.unlink(missing_ok=True)
            return pobierz_instalator(url_instalatora, na_postep)

        wznowione = juz_pobrane_bajty > 0 and odpowiedz.status_code == 206
        if not wznowione:
            if odpowiedz.status_code != 200:
                raise BladPobieraniaAktualizacji(
                    f"Serwer pobierania zwrócił błąd (HTTP {odpowiedz.status_code})."
                )
            juz_pobrane_bajty = 0  # serwer zignorowal Range (albo to pierwsza proba) - pelny plik od nowa

        dlugosc_naglowka = odpowiedz.headers.get("Content-Length")
        calkowity = (
            juz_pobrane_bajty + int(dlugosc_naglowka) if dlugosc_naglowka is not None else None
        )

        tryb_pliku = "ab" if wznowione else "wb"
        pobrane = juz_pobrane_bajty
        na_postep(pobrane, calkowity)

        try:
            with open(czesciowy, tryb_pliku) as plik:
                for kawalek in odpowiedz.iter_content(ROZMIAR_CHUNK_BAJTY):
                    if not kawalek:
                        continue
                    plik.write(kawalek)
                    pobrane += len(kawalek)
                    na_postep(pobrane, calkowity)
        except requests.exceptions.RequestException as e:
            # MUSI byc zlapane PRZED OSError ponizej -
            # requests.exceptions.RequestException dziedziczy z IOError/OSError
            # (tak zdefiniowane w samej bibliotece requests), wiec odwrotna
            # kolejnosc except-ow zlapalaby TEZ przerwania sieciowe (np.
            # zerwane polaczenie w polowie pobierania) w gałęzi OSError ponizej
            # i pokazala mylacy komunikat "brak miejsca na dysku" zamiast
            # prawdziwej przyczyny (przerwane polaczenie internetowe).
            raise BladPobieraniaAktualizacji(
                f"Pobieranie zostało przerwane - sprawdź połączenie z internetem ({e})."
            ) from e
        except OSError as e:
            raise BladPobieraniaAktualizacji(
                f"Nie udało się zapisać pliku na dysku (sprawdź wolne miejsce): {e}"
            ) from e

    czesciowy.replace(docelowy)  # atomowe oznaczenie "pobieranie kompletne"
    return docelowy


def uruchom_instalator(plik_instalatora: Path) -> None:
    """Uruchamia pobrany instalator jako calkowicie NIEZALEZNY, odlaczony
    proces - appka go nie czeka ani nie sledzi dalej, dokladnie tak jak przy
    recznym dwukliku na pobrany plik. DETACHED_PROCESS (Windows-only appka,
    tak jak reszta kodu uzywajacego win32/AppUserModelID) zapewnia, ze
    instalator przezyje zamkniecie appki, ktore nastapi zaraz po tym wywolaniu
    (patrz wolajacy w gui/windows/widok_ustawien.py - ten sam wzorzec
    zamkniecia co po przywroceniu kopii zapasowej/usunieciu profilu:
    proces_aplikacji.zatrzymaj_wszystko() + os._exit(0))."""
    subprocess.Popen(
        [str(plik_instalatora)],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
        cwd=str(plik_instalatora.parent),
    )
