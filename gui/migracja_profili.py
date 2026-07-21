"""Migracja instalacji sprzed wielu profili firm (Faza 25) do nowej struktury.

Przed ta faza appka trzymala dane pod plaskimi sciezkami: %APPDATA%/FakturyPro/
{auth.json,ksef.json,email.json,integracje.json,ustawienia.json},
%LOCALAPPDATA%/FakturyPro/logo/, baza Postgresa `faktury_pro`. Bez tej migracji
dane obecnych uzytkownikow "znikneby"
po aktualizacji appki (ekran wyboru profilu pokazalby pusta liste, mimo ze
konto ma juz skonfigurowana firme). Migracja NIE zmienia nazwy istniejacej
bazy danych (rename zywej bazy jest niepotrzebnym ryzykiem) - rejestruje ja
po prostu jako profil "legacy" wskazujacy na baze `faktury_pro`.

Wolane RAZ, na samym poczatku gui/main.py:main(), PRZED ekranem wyboru
profilu (gui/windows/ekran_wyboru_profilu.py) - dzieki temu zmigrowana firma
jest od razu widoczna na liscie. Bezpieczne wywolywac przy KAZDYM starcie
appki: kazdy krok osobno sprawdza, czy jest jeszcze co robic, wiec przerwana
w polowie migracja (np. awaria appki miedzy przeniesieniem auth.json a
ksef.json) bezpiecznie wznawia sie przy kolejnym uruchomieniu zamiast
duplikowac albo gubic dane.
"""

import json
import shutil
from pathlib import Path

from app import profil
from gui import profile_rejestr

ID_PROFILU_ZMIGROWANEGO = "legacy"
NAZWA_BAZY_ZMIGROWANEJ = "faktury_pro"  # POSTGRES_PRYWATNY_BAZA sprzed Fazy 25 - nigdy nie zmieniana


def migruj_jesli_trzeba() -> None:
    if profile_rejestr.plik_rejestru_istnieje():
        return  # juz zmigrowano, albo appka jest swieza instalacja bez zadnej "starej" firmy

    stary_katalog = profil.katalog_appdata_roaming()
    if not (stary_katalog / "auth.json").exists():
        return  # brak instalacji sprzed Fazy 25 - nic do zmigrowania

    docelowy = profil.katalog_profilu(ID_PROFILU_ZMIGROWANEGO)
    docelowy.mkdir(parents=True, exist_ok=True)

    _przenies_plik(stary_katalog / "auth.json", docelowy / "auth.json")
    _przenies_plik(stary_katalog / "ksef.json", docelowy / "ksef.json")
    _przenies_plik(stary_katalog / "email.json", docelowy / "email.json")
    _przenies_plik(stary_katalog / "integracje.json", docelowy / "integracje.json")
    _przenies_katalog(profil.katalog_appdata_lokalny() / "logo", docelowy / "logo")

    # ustawienia.json: caly plik wedruje z %APPDATA% (roaming) do NOWEGO,
    # globalnego miejsca w %LOCALAPPDATA% (patrz gui/nastawienia.py - ten
    # plik zostaje GLOBALNY, tylko jego katalog nadrzedny sie zmienia); potem
    # klucze specyficzne dla backupu sa z niego wydzielane do pliku profilu.
    globalny_plik = profil.katalog_appdata_lokalny() / "ustawienia.json"
    _przenies_plik(stary_katalog / "ustawienia.json", globalny_plik)
    _wydziel_klucze_backupu(globalny_plik, docelowy / "ustawienia_profilu.json")

    profile_rejestr.dodaj_zmigrowany(ID_PROFILU_ZMIGROWANEGO, NAZWA_BAZY_ZMIGROWANEJ)


def _przenies_plik(zrodlo: Path, docelowy: Path) -> None:
    if docelowy.exists() or not zrodlo.exists():
        return
    shutil.move(str(zrodlo), str(docelowy))


def _przenies_katalog(zrodlo: Path, docelowy: Path) -> None:
    if docelowy.exists() or not zrodlo.is_dir():
        return
    shutil.move(str(zrodlo), str(docelowy))


def _wydziel_klucze_backupu(globalny_plik: Path, docelowy_profilu: Path) -> None:
    from gui.kopia_zapasowa import KLUCZ_KATALOG_DOCELOWY, KLUCZ_OSTATNI_BACKUP

    if not globalny_plik.exists() or docelowy_profilu.exists():
        return
    try:
        dane = json.loads(globalny_plik.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(dane, dict):
        return

    wydzielone = {}
    for klucz in (KLUCZ_KATALOG_DOCELOWY, KLUCZ_OSTATNI_BACKUP):
        if klucz in dane:
            wydzielone[klucz] = dane.pop(klucz)

    docelowy_profilu.write_text(json.dumps(wydzielone), encoding="utf-8")
    globalny_plik.write_text(json.dumps(dane), encoding="utf-8")
