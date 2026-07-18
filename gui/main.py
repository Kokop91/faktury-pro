import os
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import requests

if getattr(sys, "frozen", False):
    # WeasyPrint (Faza 3) laduje Pango/fontconfig przez dlopen juz przy imporcie
    # modulu weasyprint.text.ffi - w wersji spakowanej PyInstallerem natywne
    # biblioteki (.dll) i pliki konfiguracyjne fontconfig sa dolaczone przez
    # pyinstaller-hooks-contrib (hook-weasyprint.py, patrz faktury-pro.spec), ale
    # samego WSKAZANIA fontconfigowi NA te dolaczone pliki appka musi dokonac
    # sama - inaczej fontconfig probuje wkompilowanej podczas budowania sciezki
    # z maszyny budujacej (np. C:\msys64\...), ktorej nie ma na komputerze
    # uzytkownika koncowego, i PDF generuje sie bez zadnych czcionek/tekstu.
    # MUSI byc ustawione PRZED pierwszym importem weasyprint - stad na samej
    # gorze tego pliku, przed jakimkolwiek innym importem z gui/app.
    os.environ.setdefault("FONTCONFIG_PATH", str(Path(sys._MEIPASS) / "etc" / "fonts"))  # type: ignore[attr-defined]

HOST = "127.0.0.1"
PORT = 8000
HEALTH_URL = f"http://{HOST}:{PORT}/health"
TIMEOUT_STARTU_S = 15.0
INTERWAL_POLLINGU_S = 0.3


def _serwer_odpowiada(timeout: float = 0.5) -> bool:
    try:
        odpowiedz = requests.get(HEALTH_URL, timeout=timeout)
        return odpowiedz.status_code == 200
    except requests.exceptions.RequestException:
        return False


class WatekSerwera:
    """Uruchamia FastAPI (uvicorn) WEWNATRZ tego samego procesu co GUI, na
    osobnym watku (Faza 18A).

    Etap 1/2 uruchamialy serwer jako osobny PODPROCES (`sys.executable -m
    uvicorn ...`) - to dzialalo, dopoki `sys.executable` bylo prawdziwym
    python.exe z zainstalowanym pakietem uvicorn. Po spakowaniu PyInstallerem
    `sys.executable` to sama spakowana aplikacja (nie ma w niej ogolnego
    interpretera obsługującego `-m dowolny_modul`), wiec ten mechanizm przestaje
    dzialac. Alternatywa (osobny, drugi plik .exe dla samego backendu) wymagalaby
    budowania i utrzymywania DWOCH oddzielnych paczek PyInstallera oraz
    wywolywania jednej z drugiej wzgledna sciezka, co jest krucha przy roznych
    ukladach dystrybucji (installer / przenosne archiwum ZIP / tryb
    deweloperski) - a to dokladnie ten rodzaj problemu, ktory ma zniknac w
    Fazie 18. Watek w tym samym procesie eliminuje cala te kategorie problemow:
    jeden plik wykonywalny, bez zaleznosci od wzglednych sciezek do drugiego
    procesu.

    Petla Tk (mainloop, watek glowny) i petla asyncio uvicorn (ten watek) nie
    koliduja - kazda dziala we wlasnym watku. Uzyta wersja uvicorn (>=0.35,
    patrz Server.capture_signals) sama pomija instalacje handlerow sygnalow,
    gdy nie jest wywolana z watku glownego, wiec nie trzeba tego nigdzie
    recznie wylaczac.
    """

    def __init__(self, host: str, port: int):
        import uvicorn

        from app.main import app as aplikacja_fastapi

        self._server = uvicorn.Server(
            uvicorn.Config(aplikacja_fastapi, host=host, port=port, log_level="warning")
        )
        self._watek = threading.Thread(target=self._server.run, daemon=True)

    def uruchom(self) -> None:
        self._watek.start()

    def dziala(self) -> bool:
        return self._watek.is_alive()

    def zatrzymaj(self) -> None:
        self._server.should_exit = True
        self._watek.join(timeout=5)


def _uruchom_serwer() -> WatekSerwera | None:
    """Zwraca watek serwera nalezacy do nas, albo None gdy serwer juz odpowiadal
    (np. zostal uruchomiony przez wczesniejsza sesje appki) - wtedy go nie
    zatrzymujemy przy zamknieciu okna, bo nie my go uruchomilismy.
    """
    if _serwer_odpowiada():
        return None

    watek = WatekSerwera(HOST, PORT)
    watek.uruchom()
    return watek


def _czekaj_na_serwer(watek: WatekSerwera | None) -> bool:
    if watek is None:
        return True

    start = time.monotonic()
    while time.monotonic() - start < TIMEOUT_STARTU_S:
        if not watek.dziala():
            # Watek serwera zakonczyl sie przedwczesnie - np. port zajety przez cos innego.
            return False
        if _serwer_odpowiada():
            return True
        time.sleep(INTERWAL_POLLINGU_S)
    return False


def zatrzymaj_serwer(watek: WatekSerwera | None) -> None:
    if watek is None:
        return
    watek.zatrzymaj()


def _pokaz_blad_startu(tekst: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Nie można uruchomić aplikacji", tekst)
    root.destroy()


def _uruchom_prywatny_postgres_jesli_trzeba():
    """Zwraca uruchomiony PostgresPrywatny, albo None, jesli appka dziala w
    trybie deweloperskim (DATABASE_URL podane jawnie w .env - patrz
    app.config.UZYWA_PRYWATNEGO_POSTGRESA) i laczy sie z Postgresem, ktorym
    opiekuje sie deweloper recznie, tak jak w Etapie 1/2 - w tym trybie appka
    NIE dotyka prywatnej instancji w ogole (Faza 18B jest wylacznie dla
    uzytkownika koncowego, bez wlasnego .env).

    Zwraca (postgres, blad) - `blad` to czytelny komunikat po polsku, jesli
    start albo przygotowanie schematu sie nie udalo (postgres jest wtedy juz
    zatrzymany), albo None przy powodzeniu.
    """
    from app.config import UZYWA_PRYWATNEGO_POSTGRESA

    if not UZYWA_PRYWATNEGO_POSTGRESA:
        return None, None

    from gui.postgres_serwer import PostgresPrywatny, upewnij_baze_i_migracje

    postgres = PostgresPrywatny()
    postgres.uruchom()
    if not postgres.czekaj_az_gotowy():
        postgres.zatrzymaj()
        return None, (
            "Nie udało się uruchomić wbudowanej bazy danych aplikacji.\n\n"
            "Sprawdź, czy port 55432 nie jest zajęty przez inny program."
        )

    try:
        upewnij_baze_i_migracje()
    except Exception as e:  # noqa: BLE001 - pokazujemy uzytkownikowi cokolwiek pojdzie nie tak
        postgres.zatrzymaj()
        return None, f"Nie udało się przygotować bazy danych aplikacji:\n\n{e}"

    return postgres, None


def main() -> None:
    # customtkinter wlacza automatyczne DPI awareness (SetProcessDpiAwareness) na
    # Windows juz przy imporcie modulu (patrz ScalingTracker.deactivate_automatic_dpi_awareness
    # = False domyslnie) - dla ostrego renderowania na ekranach skalowanych NIE wolno
    # wywolywac ctk.deactivate_automatic_dpi_awareness() nigdzie w kodzie appki.
    from gui import nastawienia

    nastawienia.zastosuj_tryb_wygladu()

    from gui.windows.ekran_logowania import pokaz_ekran_logowania

    if not pokaz_ekran_logowania():
        return

    postgres_prywatny, blad_postgresa = _uruchom_prywatny_postgres_jesli_trzeba()
    if blad_postgresa is not None:
        _pokaz_blad_startu(blad_postgresa)
        return

    watek = _uruchom_serwer()
    if not _czekaj_na_serwer(watek):
        zatrzymaj_serwer(watek)
        if postgres_prywatny is not None:
            postgres_prywatny.zatrzymaj()
        _pokaz_blad_startu(
            "Serwer aplikacji nie uruchomił się poprawnie.\n\n"
            "Sprawdź, czy port 8000 nie jest zajęty przez inny program "
            "i czy baza danych (Docker / Postgres) jest uruchomiona."
        )
        return

    from gui.windows.glowne_okno import GlowneOkno

    okno = GlowneOkno()

    def _przy_zamknieciu() -> None:
        okno.zapisz_geometrie()
        zatrzymaj_serwer(watek)
        if postgres_prywatny is not None:
            postgres_prywatny.zatrzymaj()
        okno.destroy()

    okno.protocol("WM_DELETE_WINDOW", _przy_zamknieciu)
    okno.mainloop()


if __name__ == "__main__":
    main()
