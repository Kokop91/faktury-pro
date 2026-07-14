import customtkinter as ctk

from gui import api_client, ikony, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_magazynu import FormularzMagazynu
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("nazwa", "Nazwa", 3),
    ("lokalizacja", "Lokalizacja", 4),
]


class PanelMagazynow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI)
        )
        pasek_naglowka.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            pasek_naglowka,
            text="Dodaj magazyn",
            image=ikony.ikona_stala("plus"),
            compound="left",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_formularz,
        ).grid(row=0, column=1)

        self._tabela = Tabela(self, kolumny=KOLUMNY)
        self._tabela.grid(row=1, column=0, sticky="nsew")

    def odswiez(self) -> None:
        def zadanie():
            return api_client.pobierz_magazyny(tylko_aktywne=True, limit=200)

        def sukces(magazyny: list[dict]) -> None:
            self._tabela.ustaw_dane(magazyny)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _otworz_formularz(self) -> None:
        FormularzMagazynu(self, on_zapisano=self.odswiez)
