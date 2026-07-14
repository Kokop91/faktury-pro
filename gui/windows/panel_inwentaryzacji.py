import customtkinter as ctk

from gui import api_client, formatowanie, ikony, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_inwentaryzacji import FormularzInwentaryzacji
from gui.windows.szczegoly_inwentaryzacji import SzczegolyInwentaryzacji
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("numer", "Numer", 2),
    ("magazyn", "Magazyn", 2),
    ("data_rozpoczecia", "Data rozpoczęcia", 2),
    ("data_zakonczenia", "Data zakończenia", 2),
    ("status", "Status", 2),
]


class PanelInwentaryzacji(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._magazyny_wg_id: dict[int, str] = {}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI)
        )
        pasek_naglowka.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            pasek_naglowka,
            text="Nowy spis",
            image=ikony.ikona_stala("plus"),
            compound="left",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_formularz,
        ).grid(row=0, column=1)

        self._tabela = Tabela(
            self, kolumny=KOLUMNY, on_wiersz_kliknij=self._otworz_szczegoly
        )
        self._tabela.grid(row=1, column=0, sticky="nsew")

    def odswiez(self) -> None:
        def zadanie():
            magazyny = api_client.pobierz_magazyny(tylko_aktywne=False, limit=200)
            inwentaryzacje = api_client.pobierz_inwentaryzacje(limit=200)
            return magazyny, inwentaryzacje

        def sukces(wynik) -> None:
            magazyny, inwentaryzacje = wynik
            self._magazyny_wg_id = {m["id"]: m["nazwa"] for m in magazyny}

            formatery = {
                "magazyn": lambda i: self._magazyny_wg_id.get(
                    i["magazyn_id"], f"#{i['magazyn_id']}"
                ),
                "data_rozpoczecia": lambda i: formatowanie.formatuj_date(
                    i["data_rozpoczecia"]
                ),
                "data_zakonczenia": lambda i: (
                    formatowanie.formatuj_date(i["data_zakonczenia"])
                    if i.get("data_zakonczenia")
                    else "—"
                ),
                "status": lambda i: formatowanie.formatuj_status_inwentaryzacji(
                    i["status"]
                ),
            }
            kolory = {
                "status": lambda i: formatowanie.kolor_statusu_inwentaryzacji(
                    i["status"]
                ),
            }
            self._tabela.ustaw_dane(inwentaryzacje, formatery=formatery, kolory=kolory)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _otworz_formularz(self) -> None:
        FormularzInwentaryzacji(self, on_zapisano=self.odswiez)

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        SzczegolyInwentaryzacji(
            self, inwentaryzacja_id=wiersz["id"], on_zmiana=self.odswiez
        )
