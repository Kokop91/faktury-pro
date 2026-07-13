import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("produkt_nazwa", "Produkt", 3),
    ("magazyn_nazwa", "Magazyn", 2),
    ("ilosc", "Ilość", 1),
    ("stan_minimalny", "Stan minimalny", 1),
]

WSZYSTKIE_MAGAZYNY = "Wszystkie magazyny"


class PanelStanowMagazynowych(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._magazyny_wg_id: dict[int, dict] = {}
        self._klucze_wg_etykiety_magazynu: dict[str, int] = {}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI)
        )

        ctk.CTkLabel(
            pasek_naglowka,
            text="Magazyn:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).pack(side="left", padx=(0, styl.ODSTEP_MALY))

        self._var_magazyn = ctk.StringVar(value=WSZYSTKIE_MAGAZYNY)
        self._menu_magazyn = ctk.CTkOptionMenu(
            pasek_naglowka,
            values=[WSZYSTKIE_MAGAZYNY],
            variable=self._var_magazyn,
            command=lambda _wartosc: self._odswiez_stany(),
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        )
        self._menu_magazyn.pack(side="left")

        self._tabela = Tabela(self, kolumny=KOLUMNY)
        self._tabela.grid(row=1, column=0, sticky="nsew")

    def odswiez(self) -> None:
        def zadanie():
            return api_client.pobierz_magazyny(tylko_aktywne=True, limit=200)

        def sukces(magazyny: list[dict]) -> None:
            self._magazyny_wg_id = {m["id"]: m for m in magazyny}
            etykiety = [WSZYSTKIE_MAGAZYNY] + [m["nazwa"] for m in magazyny]
            self._klucze_wg_etykiety_magazynu = {
                m["nazwa"]: m["id"] for m in magazyny
            }
            self._menu_magazyn.configure(values=etykiety)
            if self._var_magazyn.get() not in etykiety:
                self._var_magazyn.set(WSZYSTKIE_MAGAZYNY)
            self._odswiez_stany()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _odswiez_stany(self) -> None:
        magazyn_id = self._klucze_wg_etykiety_magazynu.get(self._var_magazyn.get())

        def zadanie():
            return api_client.pobierz_stany_magazynowe(magazyn_id=magazyn_id)

        def sukces(stany: list[dict]) -> None:
            formatery = {
                "ilosc": lambda s: formatowanie.formatuj_ilosc(
                    s["ilosc"], s["jednostka_miary"]
                ),
                "stan_minimalny": lambda s: (
                    formatowanie.formatuj_ilosc(
                        s["stan_minimalny"], s["jednostka_miary"]
                    )
                    if s["stan_minimalny"] is not None
                    else "—"
                ),
            }
            kolory = {
                klucz: (
                    lambda s: styl.KOLOR_OSTRZEZENIE
                    if s["ponizej_minimum"]
                    else styl.KOLOR_TEKST_GLOWNY
                )
                for klucz, _etykieta, _waga in KOLUMNY
            }
            self._tabela.ustaw_dane(stany, formatery=formatery, kolory=kolory)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
