import customtkinter as ctk

from gui import api_client, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_klienta import FormularzKlienta
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("nazwa", "Nazwa", 3),
    ("nip", "NIP", 1),
    ("miejscowosc", "Miejscowość", 2),
    ("email", "Email", 2),
    ("telefon", "Telefon", 1),
]


class WidokKlientow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
        )
        pasek_naglowka.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            pasek_naglowka,
            text="Klienci",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            pasek_naglowka,
            text="+ Dodaj klienta",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_formularz,
        ).grid(row=0, column=1)

        self._tabela = Tabela(self, kolumny=KOLUMNY, on_wiersz_kliknij=self._otworz_edycji)
        self._tabela.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(0, styl.ODSTEP_DUZY),
        )

    def odswiez(self) -> None:
        def zadanie():
            return api_client.pobierz_klientow(tylko_aktywni=True, limit=200)

        def sukces(klienci: list[dict]) -> None:
            self._tabela.ustaw_dane(klienci)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _otworz_formularz(self) -> None:
        FormularzKlienta(self, on_zapisano=self.odswiez)

    def _otworz_edycji(self, wiersz: dict) -> None:
        FormularzKlienta(self, on_zapisano=self.odswiez, klient=wiersz)
