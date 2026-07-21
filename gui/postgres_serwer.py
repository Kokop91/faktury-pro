"""Zarzadzanie prywatna, przenosna instancja PostgreSQL (Faza 18B, Etap 3).

Rozszerza wzorzec zarzadzania procesami wprowadzony dla serwera FastAPI
(Faza 4, zmieniony w Fazie 18A - patrz gui/main.py:WatekSerwera): appka sama
uruchamia i zatrzymuje wlasny, prywatny serwer bazy danych, uzytkownik
koncowy nigdy nie ma swiadomosci, ze PostgreSQL w ogole istnieje.

WAZNE - to jest AKTYWNE wylacznie wtedy, gdy app.config.UZYWA_PRYWATNEGO_POSTGRESA
jest prawdziwe, czyli gdy DATABASE_URL NIE jest podane jawnie w .env/zmiennej
srodowiskowej. Tryb deweloperski (z .env, jak w Etapie 1/2) nie jest tym
w ogole dotkniety - deweloper laczy sie ze swoim recznie uruchomionym
Postgresem tak jak dotychczas.

Binaria (postgres.exe, initdb.exe, pg_ctl.exe, pg_isready.exe) sa CZYSCIA
appki (dolaczone przez faktury_pro.spec, patrz scripts/pobierz_postgres_portable.py) -
katalog binariow jest wiec rozwiazywany przez app.sciezki.katalog_bazowy(),
identycznie jak szablony PDF/schematy XSD w Fazie 18A. Katalog DANYCH (zywa,
mutowalna baza) zyje NATOMIAST w %LOCALAPPDATA%/FakturyPro/pgsql-data - musi
przetrwac aktualizacje/reinstalacje samej appki, wiec nie moze siedziec w tym
samym miejscu co jej pliki programu.
"""

import subprocess
import sys
import time
from pathlib import Path

from app.config import (
    POSTGRES_PRYWATNY_BAZA,
    POSTGRES_PRYWATNY_HOST,
    POSTGRES_PRYWATNY_PORT,
    POSTGRES_PRYWATNY_UZYTKOWNIK,
    adres_prywatnego_postgresa,
)
from app.profil import katalog_appdata_lokalny
from app.sciezki import katalog_bazowy

NAZWA_KATALOGU_DANYCH = "pgsql-data"
TIMEOUT_STARTU_S = 20.0
INTERWAL_POLLINGU_S = 0.3


def _katalog_appdata() -> Path:
    # Katalog GLOBALNY (nie per-profil, Faza 25) - jedna instancja Postgresa
    # obsluguje wiele baz, jedna na profil (patrz app/profil.py, app/config.py).
    return katalog_appdata_lokalny()


def _katalog_binariow() -> Path:
    return katalog_bazowy() / "vendor" / "postgresql" / "pgsql" / "bin"


def _katalog_danych() -> Path:
    return _katalog_appdata() / NAZWA_KATALOGU_DANYCH


def _flagi_bez_okna() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


class BladPostgresaPrywatnego(Exception):
    pass


class PostgresPrywatny:
    """Uruchamia/zatrzymuje prywatna instancje PostgreSQL jako podproces -
    analogicznie do gui/main.py:WatekSerwera, ale przez prawdziwy podproces
    (postgres.exe), nie watek: to osobny program (binarka C, nie modul
    Pythona), wiec nie ma tu mozliwosci "uruchom w watku w tym samym procesie"
    tak jak zrobiono z uvicornem w Fazie 18A.
    """

    def __init__(self) -> None:
        self._proces: subprocess.Popen | None = None

    def _initdb_jesli_trzeba(self) -> None:
        katalog_danych = _katalog_danych()
        if (katalog_danych / "PG_VERSION").exists():
            return

        katalog_danych.parent.mkdir(parents=True, exist_ok=True)
        initdb = _katalog_binariow() / "initdb.exe"
        wynik = subprocess.run(
            [
                str(initdb),
                "-D", str(katalog_danych),
                "-U", POSTGRES_PRYWATNY_UZYTKOWNIK,
                "--auth=trust",
                "--encoding=UTF8",
                "--locale=C",
            ],
            capture_output=True,
            text=True,
            creationflags=_flagi_bez_okna(),
        )
        if wynik.returncode != 0:
            raise BladPostgresaPrywatnego(
                f"initdb zakonczyl sie bledem (kod {wynik.returncode}):\n{wynik.stderr}"
            )

    def uruchom(self) -> None:
        """Wykonuje initdb (jesli to pierwsze uruchomienie) i startuje
        postgres.exe jako podproces. Sam start jest nieblokujacy - czekanie
        na gotowosc robi czekaj_az_gotowy()."""
        self._initdb_jesli_trzeba()

        postgres_exe = _katalog_binariow() / "postgres.exe"
        self._proces = subprocess.Popen(
            [
                str(postgres_exe),
                "-D", str(_katalog_danych()),
                "-h", POSTGRES_PRYWATNY_HOST,
                "-p", str(POSTGRES_PRYWATNY_PORT),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_flagi_bez_okna(),
        )

    def dziala(self) -> bool:
        return self._proces is not None and self._proces.poll() is None

    def _gotowy_do_polaczen(self) -> bool:
        pg_isready = _katalog_binariow() / "pg_isready.exe"
        wynik = subprocess.run(
            [
                str(pg_isready),
                "-h", POSTGRES_PRYWATNY_HOST,
                "-p", str(POSTGRES_PRYWATNY_PORT),
                "-U", POSTGRES_PRYWATNY_UZYTKOWNIK,
            ],
            capture_output=True,
            creationflags=_flagi_bez_okna(),
        )
        return wynik.returncode == 0

    def czekaj_az_gotowy(self, timeout_s: float = TIMEOUT_STARTU_S) -> bool:
        start = time.monotonic()
        while time.monotonic() - start < timeout_s:
            if not self.dziala():
                # Proces zakonczyl sie przedwczesnie - np. port zajety przez cos innego.
                return False
            if self._gotowy_do_polaczen():
                return True
            time.sleep(INTERWAL_POLLINGU_S)
        return False

    def zatrzymaj(self) -> None:
        if self._proces is None:
            return

        pg_ctl = _katalog_binariow() / "pg_ctl.exe"
        subprocess.run(
            [str(pg_ctl), "-D", str(_katalog_danych()), "-m", "fast", "stop"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_flagi_bez_okna(),
        )
        try:
            self._proces.wait(timeout=15)
        except subprocess.TimeoutExpired:
            # pg_ctl stop sie nie udalo (np. zawieszony proces) - ostatecznosc,
            # analogicznie do zatrzymaj_serwer() w gui/main.py dla FastAPI.
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(self._proces.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                self._proces.kill()
            try:
                self._proces.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass


def upewnij_baze_i_migracje() -> None:
    """Tworzy baze `faktury_pro`, jesli jeszcze nie istnieje (swiezy katalog
    danych po initdb ma tylko domyslne bazy postgres/template1), i dociaga
    schemat do najnowszej migracji Alembic. Bezpieczne wywolywac przy kazdym
    starcie - CREATE DATABASE pomijane, gdy baza juz istnieje, `alembic
    upgrade head` jest bezoperacyjne, gdy schemat juz jest aktualny.
    """
    import psycopg2

    polaczenie = psycopg2.connect(adres_prywatnego_postgresa("postgres"))
    polaczenie.autocommit = True
    try:
        with polaczenie.cursor() as kursor:
            kursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (POSTGRES_PRYWATNY_BAZA,)
            )
            if kursor.fetchone() is None:
                # Nazwa bazy pochodzi ze stalej w kodzie (nie od uzytkownika),
                # bezpieczne bez parametryzacji - psycopg2 nie pozwala
                # parametryzowac nazw obiektow w DDL.
                kursor.execute(f"CREATE DATABASE {POSTGRES_PRYWATNY_BAZA}")
    finally:
        polaczenie.close()

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(katalog_bazowy() / "alembic.ini"))
    cfg.set_main_option("script_location", str(katalog_bazowy() / "alembic"))
    command.upgrade(cfg, "head")


def usun_baze(nazwa_bazy: str) -> None:
    """DROP DATABASE na prywatnej instancji - wolane WYLACZNIE przy usuwaniu
    profilu firmy (Faza 25, Ustawienia -> "Usun te firme"), PO zatrzymaniu
    serwera FastAPI (patrz gui/proces_aplikacji.py:zatrzymaj_serwer_fastapi) -
    dopoki jakiekolwiek polaczenie SQLAlchemy tej appki trzyma baze otwarta,
    DROP DATABASE by sie nie udal. `WITH (FORCE)` (PostgreSQL 13+) rozlacza
    dodatkowo wszelkie pozostale sesje jako ostatnia gwarancja.

    `nazwa_bazy` NIGDY nie pochodzi bezposrednio od uzytkownika - zawsze z
    wpisu w gui/profile_rejestr.py (wygenerowanego przy tworzeniu profilu),
    wiec f-string bez parametryzacji ma ten sam profil bezpieczenstwa co
    CREATE DATABASE kilka linii wyzej w tym samym pliku."""
    import psycopg2

    polaczenie = psycopg2.connect(adres_prywatnego_postgresa("postgres"))
    polaczenie.autocommit = True
    try:
        with polaczenie.cursor() as kursor:
            kursor.execute(f'DROP DATABASE IF EXISTS "{nazwa_bazy}" WITH (FORCE)')
    finally:
        polaczenie.close()
