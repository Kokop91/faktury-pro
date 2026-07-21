"""Przypomnienie o kopii zapasowej przy starcie appki (Faza 22) - ten sam
wzorzec co DialogZaleglychCyklicznych (Faza 15): appka desktopowa nie dziala
24/7, wiec zamiast systemowego harmonogramu sprawdzamy stan RAZ, przy kazdym
uruchomieniu. Nigdy nie wykonuje backupu samo z siebie - tylko informuje i
przekierowuje do Ustawien, gdzie uzytkownik swiadomie podaje haslo szyfrowania
(patrz gui/windows/dialog_kopii_zapasowej.py)."""
from typing import Callable

import customtkinter as ctk

from gui import styl


class DialogPrzypomnieniaBackupu(ctk.CTkToplevel):
    def __init__(self, master, nigdy_skonfigurowano: bool, dni_od_ostatniego: int | None, on_przejdz: Callable[[], None]):
        super().__init__(master)
        self.title("Kopia zapasowa")
        self.geometry("440x220")
        self.resizable(False, False)
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda _z: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._on_przejdz = on_przejdz

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)

        if nigdy_skonfigurowano:
            tytul = "Nie skonfigurowano kopii zapasowej"
            tresc = (
                "Wszystkie dane tej aplikacji (faktury, klienci, magazyn) są "
                "przechowywane wyłącznie lokalnie, na tym komputerze. Skonfiguruj "
                "kopię zapasową w Ustawieniach, żeby zabezpieczyć się przed "
                "utratą danych przy awarii dysku."
            )
        elif dni_od_ostatniego is None:
            # Lokalizacja kopii JEST ustawiona (inaczej nigdy_skonfigurowano
            # bylby True), ale zadna kopia jeszcze nie powstala - odrebny
            # wariant od "nieaktualna", zeby nie interpolowac None w tresci.
            tytul = "Nie wykonano jeszcze kopii zapasowej"
            tresc = (
                "Lokalizacja kopii zapasowych jest już ustawiona, ale nie "
                "wykonano jeszcze żadnej kopii. Zalecamy wykonanie pierwszej "
                "kopii w Ustawieniach."
            )
        else:
            tytul = "Kopia zapasowa jest nieaktualna"
            tresc = (
                f"Ostatnia kopia zapasowa została wykonana {dni_od_ostatniego} dni "
                "temu. Zalecamy wykonanie nowej kopii w Ustawieniach."
            )

        ctk.CTkLabel(
            kontener, text=tytul, font=styl.NAGLOWEK_2, text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        ctk.CTkLabel(
            kontener, text=tresc, font=styl.CZCIONKA_TRESC, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=380, justify="left", anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        pasek = ctk.CTkFrame(kontener, fg_color="transparent")
        pasek.pack(fill="x", side="bottom")
        pasek.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            pasek, text="Później", fg_color="transparent", border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE, text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY, command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        ctk.CTkButton(
            pasek, text="Przejdź do Ustawień", fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER, command=self._przejdz,
        ).grid(row=0, column=1, sticky="ew")

    def _przejdz(self) -> None:
        self.destroy()
        self._on_przejdz()
