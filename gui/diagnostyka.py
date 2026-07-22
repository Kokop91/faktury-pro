"""Pakiet diagnostyczny na potrzeby wsparcia zdalnego (Faza 26).

Znajomy uzytkownik koncowy jest osoba nietechniczna - nie potrafi opisac
bledu ani samodzielnie znalezc pliku logow. Ten modul pakuje w JEDEN plik
ZIP wszystko, co potrzebne do zdalnej diagnozy: log aplikacji, numer wersji,
ktory profil firmy byl aktywny i podstawowe informacje o systemie. Appka
NIC nie wysyla sama przez internet (w odroznieniu od sprawdzania aktualizacji,
ktore i tak tylko CZYTA plik z GitHub) - plik ZIP ląduje na Pulpicie, a
uzytkownik wysyla go recznie mailem, sam opisujac problem.

CELOWO NIE trafiaja do pakietu: hash hasla appki (gui/auth.py), token KSeF
nawet zaszyfrowany (app/services/ksef_ustawienia.py), haslo/klucz SMTP
(app/services/email_ustawienia.py), klucz produkcyjny GUS
(app/services/integracje_ustawienia.py), haslo szyfrowania kopii zapasowej
(to ostatnie i tak NIGDZIE nie jest zapisywane - gui/kopia_zapasowa.py) ani
zadne dane biznesowe (klienci, faktury, magazyn) - appka nie dolacza zadnego
zrzutu bazy danych, tylko log aplikacji + tekst diagnostyczny wygenerowany
przez ten modul.

Przeglad kodu PRZED napisaniem tego modulu (nie zgadywane): jedyne miejsce w
calej appce logujace na poziomie WARNING+ poza samym uvicornem to
gui/windows/glowne_okno.py (4 wywolania _log.warning przy nieudanych
sprawdzeniach startowych - KSeF/faktury cykliczne/przypomnienia/odznaka
kosztow), kazde loguje wylacznie tresc zlapanego wyjatku sieciowego (np.
timeout, HTTP error) - zaden z nich nie ma dostepu do hasel/tokenow w tym
miejscu kodu. Mimo to log jest DODATKOWO filtrowany linia-po-linii wzgledem
slow kluczowych zwiazanych z sekretami (_WZORCE_WRAZLIWE) jako zabezpieczenie
defense-in-depth - appka nie polega wylacznie na tym, ze dzisiejszy przeglad
kodu jest wciaz aktualny przy kazdej przyszlej zmianie.
"""

import platform
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app import profil
from app.wersja import WERSJA
from gui import profile_rejestr

# Adres, na ktory appka radzi wyslac gotowy pakiet - CELOWO placeholder,
# wymaga uzupelnienia prawdziwym adresem wsparcia przed przekazaniem appki
# realnemu uzytkownikowi koncowemu (patrz CHECKLIST_WYDANIA.md).
ADRES_WSPARCIA = "ADRES-WSPARCIA-DO-UZUPELNIENIA@przyklad.pl"

# app.log NIE jest rotowany (patrz gui/main.py:_skonfiguruj_logowanie) - rosnie
# bez konca przez cale zycie instalacji. Zeby ZIP zostal maly i szybki do
# wyslania mailem, dolaczamy tylko koniec pliku powyzej tego rozmiaru.
ROZMIAR_MAX_LOGU_BAJTY = 2_000_000
LICZBA_OSTATNICH_BLEDOW = 50

_WZORCE_WRAZLIWE = re.compile(
    r"(?i)(hasl|password|token|klucz_produkcyjny|secret|cryptprotectdata|"
    r"cryptunprotectdata|postgresql://[^\s]+:[^\s]+@)"
)


def _plik_logu() -> Path:
    return profil.katalog_appdata_lokalny() / "logs" / "app.log"


def _przefiltruj_log(tekst: str) -> str:
    """Usuwa CALE linie pasujace do wzorcow zwiazanych z sekretami - patrz
    docstring modulu. Usuwanie calej linii (nie samej wartosci), bo appka nie
    zaklada z gory formatu logowanej tresci."""
    wynik = []
    for linia in tekst.splitlines():
        if _WZORCE_WRAZLIWE.search(linia):
            wynik.append("[LINIA USUNIĘTA PRZEZ FILTR DANYCH WRAŻLIWYCH]")
        else:
            wynik.append(linia)
    return "\n".join(wynik)


def _wczytaj_log_przyciety() -> str | None:
    """Zwraca przefiltrowana, ewentualnie przycieta tresc app.log, albo None,
    jesli plik jeszcze nie istnieje (np. appka jeszcze nigdy nie napotkala
    ostrzezenia, albo dziala w trybie deweloperskim - tam logi ida na
    konsole, nie do pliku, patrz gui/main.py:_skonfiguruj_logowanie)."""
    plik = _plik_logu()
    if not plik.exists():
        return None
    surowe = plik.read_bytes()
    ucieto = len(surowe) > ROZMIAR_MAX_LOGU_BAJTY
    if ucieto:
        surowe = surowe[-ROZMIAR_MAX_LOGU_BAJTY:]
    tekst = _przefiltruj_log(surowe.decode("utf-8", errors="replace"))
    if ucieto:
        tekst = (
            "[... starszy fragment pliku logu pominięty, plik przekracza 2 MB ...]\n"
            + tekst
        )
    return tekst


def _wyodrebnij_ostatnie_bledy(tekst_logu: str) -> str:
    linie_bledow = [
        linia
        for linia in tekst_logu.splitlines()
        if " WARNING " in linia or " ERROR " in linia or " CRITICAL " in linia
    ]
    if not linie_bledow:
        return "Brak zarejestrowanych ostrzeżeń/błędów w dostępnym fragmencie logu."
    return "\n".join(linie_bledow[-LICZBA_OSTATNICH_BLEDOW:])


def _info_o_wersji_i_profilu() -> str:
    wiersze = [
        f"Faktury Pro, wersja: {WERSJA}",
        f"Data wygenerowania pakietu: {datetime.now(timezone.utc).isoformat()}",
    ]
    profil_id = profil.id_profilu_aktywnego()
    if profil_id is None:
        wiersze.append("Tryb: deweloperski (bez profili firm)")
    else:
        wpis = profile_rejestr.pobierz(profil_id)
        nazwa = wpis.nazwa_wyswietlana if wpis else None
        wiersze.append(
            f"Aktywny profil firmy w chwili zgłoszenia: {nazwa or '(nieskonfigurowany)'} "
            f"(identyfikator wewnętrzny: {profil_id})"
        )
        wiersze.append(
            f"Liczba profili firm skonfigurowanych na tym komputerze: "
            f"{len(profile_rejestr.wczytaj_wszystkie())}"
        )
        wiersze.append(
            "UWAGA: dołączony log aplikacji jest WSPÓLNY dla wszystkich profili "
            "na tym komputerze (appka obsługuje tylko jeden profil na raz, ale "
            "zapisuje do jednego pliku logu niezależnie od tego, który profil "
            "był akurat otwarty) - może więc zawierać wpisy z sesji innych firm."
        )
    return "\n".join(wiersze)


def _info_systemowe() -> str:
    wiersze = [f"System: {platform.platform()}"]
    try:
        release, wersja_build, _csd, _ptype = platform.win32_ver()
        wiersze.append(f"Windows: {release} (build {wersja_build})")
    except Exception as e:
        wiersze.append(f"Windows: nie udało się odczytać ({e})")

    try:
        import win32api

        stan = win32api.GlobalMemoryStatus()
        wiersze.append(
            f"Pamięć RAM: {stan['AvailPhys'] / (1024 ** 3):.1f} GB wolne z "
            f"{stan['TotalPhys'] / (1024 ** 3):.1f} GB (obciążenie {stan['MemoryLoad']}%)"
        )
    except Exception as e:
        wiersze.append(f"Pamięć RAM: nie udało się odczytać ({e})")

    try:
        calkowity, _uzyty, wolny = shutil.disk_usage(profil.katalog_appdata_lokalny())
        wiersze.append(
            f"Miejsce na dysku (dane aplikacji): {wolny / (1024 ** 3):.1f} GB wolne "
            f"z {calkowity / (1024 ** 3):.1f} GB"
        )
    except Exception as e:
        wiersze.append(f"Miejsce na dysku: nie udało się odczytać ({e})")

    return "\n".join(wiersze)


def _katalog_docelowy() -> Path:
    """Pulpit uzytkownika - najbardziej oczywiste, zawsze widoczne miejsce dla
    osoby nietechnicznej. Rozwiazywany przez prawdziwe Windows "known folder"
    (dziala poprawnie tez wtedy, gdy Pulpit jest przekierowany przez OneDrive,
    w odroznieniu od zwyklego Path.home() / "Desktop"), z cichym fallbackiem
    na ten prostszy wariant, gdyby API bylo z jakiegos powodu niedostepne."""
    try:
        from win32comext.shell import shell, shellcon

        return Path(shell.SHGetKnownFolderPath(shellcon.FOLDERID_Desktop, 0, None))
    except Exception:
        return Path.home() / "Desktop"


def utworz_pakiet_diagnostyczny() -> Path:
    """Tworzy plik ZIP na Pulpicie z logiem appki (przefiltrowanym i
    ewentualnie przycietym), wyodrębnionymi ostatnimi ostrzeżeniami/błędami,
    numerem wersji, aktywnym profilem firmy i podstawowymi informacjami o
    systemie. Zwraca ścieżkę utworzonego pliku."""
    katalog_docelowy = _katalog_docelowy()
    katalog_docelowy.mkdir(parents=True, exist_ok=True)

    znacznik_czasu = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    docelowy = katalog_docelowy / f"faktury-pro-diagnostyka-{znacznik_czasu}.zip"

    tekst_logu = _wczytaj_log_przyciety()

    with zipfile.ZipFile(docelowy, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("wersja_i_profil.txt", _info_o_wersji_i_profilu())
        zf.writestr("system.txt", _info_systemowe())
        if tekst_logu is not None:
            zf.writestr("app.log", tekst_logu)
            zf.writestr("ostatnie_bledy.txt", _wyodrebnij_ostatnie_bledy(tekst_logu))
        else:
            zf.writestr(
                "app.log_BRAK.txt",
                "Plik logu nie istnieje. Może to oznaczać, że aplikacja jeszcze "
                "nigdy nie napotkała ostrzeżenia/błędu, albo że działa w trybie "
                "deweloperskim (logi trafiają wtedy na konsolę, nie do pliku).",
            )

    return docelowy
