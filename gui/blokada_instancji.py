"""Blokada pojedynczej instancji appki - bez niej dwa jednoczesnie dzialajace
procesy Faktury Pro (przypadkowy podwojny klik w skrot, albo ponowne
uruchomienie zanim poprzedni proces zdazyl sie w pelni zamknac) probowalyby
naraz zajac ten sam port lokalnego serwera FastAPI (gui/main.py:PORT) i tę
sama prywatna instancje PostgreSQL (Faza 18B) - dla uzytkownika nietechnicznego
konczyloby sie to niejasnymi bledami startu zamiast prostego "juz uruchomione".

Mechanizm: nazwany obiekt jadra Windows (Mutex) przez ctypes, NIE plik blokady
z reczne sprawdzanym PID. Swiadomy wybor: PID-w-pliku ma realny, choc rzadki
problem - po restarcie systemu ten sam PID moze zostac przydzielony zupelnie
innemu, niepowiazanemu procesowi, co dawaloby falszywe "appka wciaz dziala".
Mutex nie ma tej wady i - co najwazniejsze dla przypadku "appka zabita w
Menedzerze Zadan" - System Windows SAM zwalnia mutex, gdy proces, ktory go
trzyma, konczy dzialanie w DOWOLNY sposob (normalne zamkniecie, awaria,
TerminateProcess) - odpornosc na "osierocona" blokade jest wiec wlasciwoscia
samego systemu operacyjnego, nie logiki appki. To rowniez oznacza, ze appka
NIE musi pilnowac zwolnienia blokady na kazdej mozliwej sciezce wyjscia z
main() (wczesny return przy nieudanym logowaniu, przerwanym kreatorze itp.) -
nawet gdyby ktorys z nich pominal jawne zwolnij_blokade(), zamkniecie procesu
Pythona i tak zwolni mutex. Jawne wywolanie w _przy_zamknieciu() (gui/main.py)
zostaje dla natychmiastowego zwolnienia przy normalnym zamknieciu, nie jako
jedyna linia obrony.
"""

import ctypes
from ctypes import wintypes

NAZWA_MUTEXU = "Local\\FakturyPro_PojedynczaInstancja"
ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9

_uchwyt_mutexu: int | None = None


def uzyskaj_blokade() -> bool:
    """Probuje uzyskac blokade pojedynczej instancji. Zwraca True, jesli ta
    appka jest jedyna dzialajaca instancja (blokada uzyskana - appka moze
    kontynuowac start), False jesli inna instancja juz dziala."""
    global _uchwyt_mutexu

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    uchwyt = kernel32.CreateMutexW(None, wintypes.BOOL(False), NAZWA_MUTEXU)

    if not uchwyt:
        # CreateMutexW sam sie nie udal (bardzo rzadkie) - nie blokujemy startu
        # appki z powodu samej ochrony przed druga instancja.
        return True

    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(uchwyt)
        return False

    _uchwyt_mutexu = uchwyt
    return True


def zwolnij_blokade() -> None:
    global _uchwyt_mutexu
    if _uchwyt_mutexu is None:
        return
    ctypes.windll.kernel32.CloseHandle(_uchwyt_mutexu)
    _uchwyt_mutexu = None


_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def aktywuj_istniejace_okno() -> bool:
    """Znajduje widoczne okno juz dzialajacej instancji (tytul zawsze zaczyna
    sie od "Faktury Pro" - ekran logowania/splash startu/kreator/glowne okno,
    patrz gui/windows/*.py) i probuje przeniesc je na wierzch. Zwraca True,
    jesli znaleziono i probowano aktywowac okno (nawet jesli Windows odmowi
    oddania fokusu - to twarde ograniczenie systemu, nie bledu appki), False
    jesli zadnego pasujacego okna nie znaleziono (appka pokaze wtedy sam
    komunikat, bez proby aktywacji)."""
    user32 = ctypes.windll.user32
    znalezione: list[int] = []

    def _callback(hwnd: int, _lparam: int) -> bool:
        dlugosc = user32.GetWindowTextLengthW(hwnd)
        if dlugosc == 0 or not user32.IsWindowVisible(hwnd):
            return True
        bufor = ctypes.create_unicode_buffer(dlugosc + 1)
        user32.GetWindowTextW(hwnd, bufor, dlugosc + 1)
        if bufor.value.startswith("Faktury Pro"):
            znalezione.append(hwnd)
            return False  # przerwij enumeracje - juz mamy co trzeba
        return True

    user32.EnumWindows(_WNDENUMPROC(_callback), 0)

    if not znalezione:
        return False

    hwnd = znalezione[0]
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True
