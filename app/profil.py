"""Rozwiazywanie sciezek dla wielu, niezaleznych profili firm (Faza 25).

Jedno, wspolne zrodlo prawdy dla "gdzie na dysku zyja dane danego profilu" -
zastepuje 6 niezaleznie zduplikowanych helperow `_katalog_appdata()`/
`_katalog_konfiguracji()`, ktore istnialy osobno w gui/postgres_serwer.py,
gui/logo.py, gui/auth.py, gui/nastawienia.py i app/services/ksef_ustawienia.py
przed ta faza.

Mechanizm przekazania "ktory profil jest aktywny" do reszty procesu: zmienne
srodowiskowe (nie stan modulu w pamieci) - ustawiane RAZ, na samym poczatku
gui/main.py:main(), zanim jakikolwiek kod zaimportuje app.config. Powod:
app/config.py oblicza DATABASE_URL/POSTGRES_PRYWATNY_BAZA jako stale modulu
przy PIERWSZYM imporcie (patrz tamten plik) - jesli ten import nastapi zanim
profil zostanie wybrany, appka polaczy sie z zla baza (albo domyslna
"faktury_pro") i juz nigdy sie nie przelaczy w ramach tego samego procesu.
Zmienna srodowiskowa (zamiast np. globalnej zmiennej w tym module) jest
odporna na kolejnosc importow miedzy app.profil i app.config - dziala
niezaleznie od tego, ktory z nich zostanie zaimportowany jako pierwszy.

Lezy w app/, nie gui/, celowo: app/config.py musi importowac stad nazwe
zmiennej srodowiskowej, a warstwa app/ nigdy nie zalezy od gui/ (odwrotna
zaleznosc byla by cyklem).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# KRYTYCZNE (Faza 25, blad znaleziony po pierwszym realnym uzyciu): czy_tryb_deweloperski()
# nizej sprawdza DATABASE_URL w os.environ, ale plik .env sam z siebie NIE trafia do
# os.environ - trzeba go jawnie wczytac (python-dotenv). app/config.py robi to tez
# (load_dotenv() na gorze tamtego modulu), ale ten modul (app/profil.py) jest CELOWO
# importowany i uzywany (gui/main.py) PRZED jakimkolwiek importem app.config - inaczej
# profil zostalby wybrany PO zamrozeniu POSTGRES_PRYWATNY_BAZA. Bez tego wywolania tutaj
# czy_tryb_deweloperski() zwracalby False na czysto (mimo istniejacego .env z DATABASE_URL),
# appka pokazywalaby ekran wyboru profilu i pisala haslo do auth.json per-profilu, a
# PO ZAIMPORTOWANIU app.config kilka linijek pozniej (ktory dopiero wtedy wczytuje .env)
# UZYWA_PRYWATNEGO_POSTGRESA nagle wychodzilo False - appka laczyla sie z ZUPELNIE INNA,
# plaska baza deweloperska z .env, ignorujac wybrany profil. Skutek: haslo sprawdzane
# wzgledem jednego profilu, dane firmy/faktur z zupelnie innej bazy - i przy kolejnym
# uruchomieniu latwo trafic na inny profil w tym samym pickerze, co daje "nieprawidlowe
# haslo" mimo poprawnego hasla ustawionego wczesniej. load_dotenv() jest idempotentne
# (bezpieczne wywolac powtornie w app/config.py) i NIE nadpisuje juz ustawionych zmiennych
# srodowiskowych, wiec to wywolanie nie zmienia zachowania appki u uzytkownika koncowego
# (bez .env w ogole) ani gdy .env jest juz wczytany przez inny mechanizm (np. IDE).
load_dotenv()

NAZWA_KATALOGU = "FakturyPro"
NAZWA_PODKATALOGU_PROFILI = "profiles"

ZMIENNA_ID_PROFILU = "FAKTURY_PRO_PROFIL_ID"
ZMIENNA_BAZA_PROFILU = "FAKTURY_PRO_PROFIL_BAZA"


def czy_tryb_deweloperski() -> bool:
    """Ta sama definicja co app.config.UZYWA_PRYWATNEGO_POSTGRESA (odwrotna),
    ale bez importu app.config - samo zaimportowanie tamtego modulu zamraza
    DATABASE_URL na stale dla calego procesu (patrz docstring modulu wyzej).
    Uzywane w gui/main.py PRZED jakakolwiek decyzja o pokazaniu ekranu wyboru
    profilu: w trybie deweloperskim (.env z jawnym DATABASE_URL) profile w
    ogole nie istnieja - appka laczy sie z baza, ktora administruje deweloper,
    dokladnie jak przed Faza 25."""
    return "DATABASE_URL" in os.environ


def katalog_appdata_lokalny() -> Path:
    """%LOCALAPPDATA%/FakturyPro - katalog GLOBALNY, wspolny dla wszystkich
    profili (rejestr profili, katalog danych prywatnego Postgresa, globalne
    ustawienia UI takie jak tryb wygladu)."""
    podstawa = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(podstawa) / NAZWA_KATALOGU


def katalog_appdata_roaming() -> Path:
    """%APPDATA%/FakturyPro - WYLACZNIE do wykrycia instalacji sprzed Fazy 25
    przy migracji (gui/migracja_profili.py). Nowe, per-profilowe dane NIGDY
    tu juz nie trafiaja - wszystko po tej fazie zyje pod katalog_profilu()."""
    if os.name == "nt":
        podstawa = os.environ.get("APPDATA") or str(Path.home())
    else:
        podstawa = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(podstawa) / NAZWA_KATALOGU


def katalog_profilu(profil_id: str) -> Path:
    return katalog_appdata_lokalny() / NAZWA_PODKATALOGU_PROFILI / profil_id


def ustaw_aktywny_profil(profil_id: str, nazwa_bazy: str) -> None:
    """Wolane DOKLADNIE RAZ, na samym poczatku gui/main.py:main() (zaraz po
    ekranie wyboru profilu), PRZED jakimkolwiek importem app.config w tym
    procesie. Po tym wywolaniu app.config.POSTGRES_PRYWATNY_BAZA (i wiec
    DATABASE_URL) rozwiaze sie do bazy TEGO profilu, bez zadnej dalszej
    interwencji - patrz app/config.py."""
    os.environ[ZMIENNA_ID_PROFILU] = profil_id
    os.environ[ZMIENNA_BAZA_PROFILU] = nazwa_bazy


def id_profilu_aktywnego() -> str | None:
    return os.environ.get(ZMIENNA_ID_PROFILU)


def katalog_aktywnego_profilu() -> Path:
    """Katalog per-profilowych danych (auth.json/ksef.json/logo/
    ustawienia_profilu.json) AKTYWNEGO profilu. W trybie deweloperskim
    (id_profilu_aktywnego() is None, bo ekran wyboru profilu jest wtedy w
    ogole pomijany - patrz czy_tryb_deweloperski) spada z powrotem na wspolny
    katalog globalny, identycznie jak appka dzialala przed Faza 25."""
    profil_id = id_profilu_aktywnego()
    if profil_id is None:
        return katalog_appdata_lokalny()
    return katalog_profilu(profil_id)
