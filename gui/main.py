import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import requests

PROJEKT_ROOT = Path(__file__).resolve().parent.parent
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


def _uruchom_serwer() -> subprocess.Popen | None:
    """Zwraca proces serwera nalezacy do nas, albo None gdy serwer juz odpowiadal
    (np. zostal uruchomiony przez wczesniejsza sesje appki) - wtedy go nie
    zatrzymujemy przy zamknieciu okna, bo nie my go uruchomilismy.
    """
    if _serwer_odpowiada():
        return None

    flagi_utworzenia = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", str(PORT)],
        cwd=str(PROJEKT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flagi_utworzenia,
    )


def _czekaj_na_serwer(proces: subprocess.Popen | None) -> bool:
    if proces is None:
        return True

    start = time.monotonic()
    while time.monotonic() - start < TIMEOUT_STARTU_S:
        if proces.poll() is not None:
            # Proces zakonczyl sie przedwczesnie - np. port zajety przez cos innego.
            return False
        if _serwer_odpowiada():
            return True
        time.sleep(INTERWAL_POLLINGU_S)
    return False


def zatrzymaj_serwer(proces: subprocess.Popen | None) -> None:
    if proces is None:
        return

    if sys.platform == "win32":
        # proces.terminate() zabija tylko bezposredniego potomka. Na tej maszynie baza
        # interpretera tego venv to Python ze Sklepu Windows, ktory uruchamia sie przez
        # alias wykonawczy Windows tworzacy dodatkowy proces potomny - terminate() na
        # samym proces.pid nie gwarantuje wiec zabicia realnego serwera. taskkill /T
        # zabija cale drzewo procesow, wiec serwer na pewno przestaje nasluchiwac.
        subprocess.run(
            ["taskkill", "/PID", str(proces.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        proces.terminate()

    try:
        proces.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proces.kill()


def _pokaz_blad_startu(tekst: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Nie można uruchomić aplikacji", tekst)
    root.destroy()


def main() -> None:
    ctk.set_appearance_mode("Light")

    proces = _uruchom_serwer()
    if not _czekaj_na_serwer(proces):
        zatrzymaj_serwer(proces)
        _pokaz_blad_startu(
            "Serwer aplikacji nie uruchomił się poprawnie.\n\n"
            "Sprawdź, czy port 8000 nie jest zajęty przez inny program "
            "i czy baza danych (Docker / Postgres) jest uruchomiona."
        )
        return

    from gui.windows.glowne_okno import GlowneOkno

    okno = GlowneOkno()

    def _przy_zamknieciu() -> None:
        zatrzymaj_serwer(proces)
        okno.destroy()

    okno.protocol("WM_DELETE_WINDOW", _przy_zamknieciu)
    okno.mainloop()


if __name__ == "__main__":
    main()
