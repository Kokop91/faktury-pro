from typing import Callable

import customtkinter as ctk

from gui import styl

_OPISY_PROBLEMOW = {
    "robocza": "Faktura robocza — zostanie POMINIĘTA w ewidencji (nie ma jeszcze mocy prawnej)",
    "brak_nip_klienta": "Brak NIP klienta — w JPK zostanie wpisane „brak” zamiast numeru",
}


class DialogGotowosciJPK(ctk.CTkToplevel):
    """Ostrzezenie PRZED wygenerowaniem JPK_V7 (wymagane w specyfikacji Fazy 13) -
    appka NIGDY nie generuje "po cichu" pliku pomijajacego faktury robocze albo
    z niekompletnymi danymi klienta; uzytkownik musi to swiadomie zobaczyc i
    potwierdzic, ze rozumie konsekwencje, zanim faktycznie powstanie plik XML."""

    def __init__(self, master, wynik: dict, on_kontynuuj: Callable[[], None]):
        super().__init__(master)
        self.title("Sprawdzenie okresu przed generowaniem JPK_V7")
        self.geometry("620x480")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda _z: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._on_kontynuuj = on_kontynuuj

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        problemy = wynik.get("problemy", [])
        ctk.CTkLabel(
            self,
            text=f"Znaleziono {len(problemy)} potencjalnych problemów w tym okresie",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_OSTRZEZENIE,
        ).grid(row=0, column=0, sticky="w", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI))

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(row=1, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY)
        przewijany.grid_columnconfigure(0, weight=1)

        for indeks, pozycja in enumerate(problemy):
            wiersz = ctk.CTkFrame(
                przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
            )
            wiersz.grid(row=indeks, column=0, sticky="ew", pady=(0, styl.ODSTEP_MALY))
            wiersz.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                wiersz,
                text=f"{pozycja['numer']} — {pozycja['klient_nazwa']}",
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_MALY, 0))

            ctk.CTkLabel(
                wiersz,
                text=_OPISY_PROBLEMOW.get(pozycja["problem"], pozycja["problem"]),
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                anchor="w",
                wraplength=520,
                justify="left",
            ).grid(row=1, column=0, sticky="w", padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_MALY))

        pasek_przyciskow = ctk.CTkFrame(self, fg_color="transparent")
        pasek_przyciskow.grid(row=2, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)
        pasek_przyciskow.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            pasek_przyciskow,
            text="Anuluj",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))

        ctk.CTkButton(
            pasek_przyciskow,
            text="Kontynuuj mimo to",
            fg_color=styl.KOLOR_OSTRZEZENIE,
            hover_color=styl.KOLOR_OSTRZEZENIE,
            command=self._kontynuuj,
        ).grid(row=0, column=1, sticky="ew")

    def _kontynuuj(self) -> None:
        self.destroy()
        self._on_kontynuuj()
