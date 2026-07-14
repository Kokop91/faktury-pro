import tkinter as tk
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from gui import styl


class OknoFormularza(ctk.CTkToplevel):
    """Wspolna baza dla wszystkich modalnych okien (formularzy i szczegolow) -
    Faza 16C. Ujednolica to, co kazde z nich dotad powtarzalo osobno
    (transient/grab_set) i dodaje:
    - Esc oraz klikniecie X pytaja o potwierdzenie, jesli sa niezapisane zmiany
    - Ctrl+S wywoluje zarejestrowana akcje zapisu (jesli formularz ja rejestruje)

    Wykrywanie niezapisanych zmian dziala przez porownanie zrzutu wartosci
    wszystkich pol (Entry/Textbox/CheckBox/OptionMenu/SegmentedButton) w
    momencie wywolania `zapamietaj_stan_poczatkowy()` z ich biezacym stanem -
    dziala automatycznie, bez recznego oznaczania "dirty" w kazdym formularzu
    z osobna. Okna bez pol edycyjnych (czysty podglad) po prostu nigdy nie
    wykryja zmiany, wiec Esc zamyka je od razu - to zamierzone.
    """

    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()

        self._stan_poczatkowy: dict | None = None
        self._akcja_zapisu: Callable[[], None] | None = None
        self._przycisk_zapisu: ctk.CTkButton | None = None

        self.protocol("WM_DELETE_WINDOW", self._zamknij_z_potwierdzeniem)
        self.bind("<Escape>", lambda _z: self._zamknij_z_potwierdzeniem())

    def ustaw_akcje_zapisu(
        self, akcja: Callable[[], None], przycisk: ctk.CTkButton | None = None
    ) -> None:
        """Rejestruje akcje wywolywana pod Ctrl+S - zwykle ta sama funkcja co
        `command` glownego przycisku zapisu. `przycisk`, jesli podany, jest
        sprawdzany pod katem stanu "disabled" (zapis juz w toku) zeby Ctrl+S
        nie wywolal podwojnego zapisu."""
        self._akcja_zapisu = akcja
        self._przycisk_zapisu = przycisk
        self.bind("<Control-s>", lambda _z: self._wywolaj_ctrl_s())

    def _wywolaj_ctrl_s(self) -> None:
        if self._akcja_zapisu is None:
            return
        if self._przycisk_zapisu is not None and str(
            self._przycisk_zapisu.cget("state")
        ) == "disabled":
            return
        self._akcja_zapisu()

    def zapamietaj_stan_poczatkowy(self) -> None:
        """Wywolac raz, zaraz po zbudowaniu/wypelnieniu wszystkich pol
        formularza - ten zrzut jest pozniej punktem odniesienia przy
        wykrywaniu niezapisanych zmian."""
        self._stan_poczatkowy = self._zrzut_pol()

    def ma_niezapisane_zmiany(self) -> bool:
        if self._stan_poczatkowy is None:
            return False
        return self._zrzut_pol() != self._stan_poczatkowy

    def _zrzut_pol(self) -> dict:
        zrzut: dict = {}
        self._zbierz_zrzut(self, (), zrzut)
        return zrzut

    def _zbierz_zrzut(self, widget: tk.Misc, sciezka: tuple, zrzut: dict) -> None:
        for indeks, dziecko in enumerate(widget.winfo_children()):
            sciezka_dziecka = sciezka + (indeks,)
            if isinstance(dziecko, ctk.CTkTextbox):
                zrzut[sciezka_dziecka] = dziecko.get("1.0", "end-1c")
            elif isinstance(
                dziecko,
                (
                    ctk.CTkEntry,
                    ctk.CTkCheckBox,
                    ctk.CTkOptionMenu,
                    ctk.CTkSegmentedButton,
                ),
            ):
                zrzut[sciezka_dziecka] = dziecko.get()
            self._zbierz_zrzut(dziecko, sciezka_dziecka, zrzut)

    def _zamknij_z_potwierdzeniem(self) -> None:
        if self.ma_niezapisane_zmiany() and not messagebox.askyesno(
            "Niezapisane zmiany",
            "Masz niezapisane zmiany. Zamknąć bez zapisywania?",
            parent=self,
        ):
            return
        self.destroy()
