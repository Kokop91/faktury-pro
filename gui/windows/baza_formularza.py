import tkinter as tk
from typing import Callable

import customtkinter as ctk

from gui import styl
from gui.ikona_okna import ustaw_ikone


class OknoDialogu(ctk.CTkToplevel):
    """Wspolna baza dla WSZYSTKICH modalnych okien Toplevel w aplikacji
    (Faza 16C, rozszerzone przy audycie spojnosci wizualnej) - ujednolica
    tlo wg tokenow motywu (16A), transient/grab_set, zamykanie klawiszem Esc
    i - co NAJWAZNIEJSZE - poprawna ikone okna w tytule.

    Bez `ustaw_ikone(self)` ponizej kazde okno tego typu dostaje PRAWIDLOWA
    ikone Faktury Pro tylko na chwile: customtkinter samo planuje
    `self.after(200, self._windows_set_titlebar_icon)` w konstruktorze
    KAZDEGO CTkToplevel i po 200ms podmienia ikone z powrotem na wlasna,
    ogolna ikonke customtkinter (piorko) - ALE tylko jesli `.iconbitmap()`
    nie zostal jeszcze wywolany na TEJ KONKRETNEJ instancji (customtkinter
    sledzi to per-instancja flaga `_iconbitmap_method_called`, patrz
    customtkinter/windows/ctk_toplevel.py). Ustawienie ikony `default=True`
    na glownym oknie (gui/ikona_okna.py) NIE wystarcza - dziedziczy ja tylko
    sam WM, a nie ta wewnetrzna flaga customtkinter, wiec kazdy nastepny
    CTkToplevel i tak nadpisuje ja po 200ms. To byla przyczyna zgloszonej
    "genericznej ikonki" w oknie automatycznego backupu - i dotyczyla
    KAZDEGO okna Toplevel w calej appce, nie tylko tego jednego."""

    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color=styl.KOLOR_TLO)
        ustaw_ikone(self)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _z: self.destroy())


class OknoFormularza(OknoDialogu):
    """Wspolna baza dla wiekszych, edytowalnych modalnych okien (formularzy i
    szczegolow) - Faza 16C. Rozszerza OknoDialogu (tlo/ikona/transient/Esc) o:
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
        if self.ma_niezapisane_zmiany():
            # Import odroczony do wnetrza metody - widgets_pomocnicze.potwierdz
            # jest zbudowany na OknoDialogu z tego samego modulu, wiec import
            # na gorze pliku stworzylby cykl (baza_formularza -> widgets_pomocnicze
            # -> baza_formularza).
            from gui.widgets_pomocnicze import potwierdz

            if not potwierdz(
                self,
                "Masz niezapisane zmiany. Zamknąć bez zapisywania?",
                tytul="Niezapisane zmiany",
                tekst_tak="Zamknij bez zapisywania",
                tekst_nie="Wróć do edycji",
                niebezpieczne=True,
            ):
                return
        self.destroy()
