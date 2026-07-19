import threading
import tkinter as tk
from typing import Callable, TypeVar

import customtkinter as ctk

from gui import styl

T = TypeVar("T")


class _EkranStartu(ctk.CTk):
    """Maly splash z paskiem postepu pokazywany podczas przygotowania backendu
    (prywatny Postgres + migracje Alembic + serwer FastAPI, Faza 18D) - bez
    niego ten etap (kilka sekund, dluzej przy pierwszym initdb+migracjach) byl
    calkowicie niemy, appka sprawiala wrazenie zawieszonej miedzy zamknieciem
    ekranu logowania a pojawieniem sie glownego okna."""

    def __init__(self):
        super().__init__()
        self.title("Faktury Pro")
        self.geometry("360x160")
        self.resizable(False, False)
        self.configure(fg_color=styl.KOLOR_TLO)
        # Nie pozwalamy zamknac w trakcie przygotowywania backendu - nie ma tu
        # niczego, co dałoby sie bezpiecznie przerwac w polowie initdb/migracji.
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)

        ctk.CTkLabel(
            kontener,
            text="Faktury Pro",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(pady=(0, styl.ODSTEP_SREDNI))

        self._etykieta_status = ctk.CTkLabel(
            kontener,
            text="Przygotowywanie aplikacji...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_status.pack(pady=(0, styl.ODSTEP_MALY))

        pasek = ctk.CTkProgressBar(kontener, mode="indeterminate")
        pasek.pack(fill="x")
        pasek.start()

    def ustaw_status(self, tekst: str) -> None:
        self._etykieta_status.configure(text=tekst)


def pokaz_podczas(zadanie: Callable[[Callable[[str], None]], T]) -> T:
    """Pokazuje pasek postepu podczas wykonania `zadanie` w osobnym watku, zeby
    nie zamrazac UI. `zadanie` dostaje callback do aktualizacji tekstu statusu -
    wywolywany z watku w tle, bezpiecznie przekazywany na watek Tk przez
    .after() (ten sam wzorzec co gui/watki.py:uruchom_w_tle). Blokuje na
    wlasnym mainloop do zakonczenia zadania, zwraca jego wynik."""
    okno = _EkranStartu()
    wynik: dict[str, T] = {}

    def zglos_status(tekst: str) -> None:
        try:
            okno.after(0, lambda: okno.ustaw_status(tekst))
        except tk.TclError:
            pass  # okno juz zniszczone

    def watek() -> None:
        try:
            wynik["wartosc"] = zadanie(zglos_status)
        finally:
            try:
                okno.after(0, okno.destroy)
            except tk.TclError:
                pass

    threading.Thread(target=watek, daemon=True).start()
    okno.mainloop()
    return wynik["wartosc"]
