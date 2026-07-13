import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.eksport_csv import eksportuj_do_csv
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("produkt_nazwa", "Produkt", 3),
    ("magazyn_nazwa", "Magazyn", 2),
    ("ilosc", "Ilość", 1),
    ("stan_minimalny", "Stan minimalny", 1),
]

KOLUMNY_CSV = [
    ("produkt_nazwa", "Produkt"),
    ("jednostka_miary", "Jednostka"),
    ("magazyn_nazwa", "Magazyn"),
    ("ilosc", "Ilość"),
    ("stan_minimalny", "Stan minimalny"),
]

WSZYSTKIE_MAGAZYNY = "Wszystkie magazyny"


class PanelRaportPonizejMinimum(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._klucze_wg_etykiety_magazynu: dict[str, int] = {}
        self._stany: list[dict] = []

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(row=0, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI))
        pasek_naglowka.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            pasek_naglowka,
            text="Magazyn:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=0, padx=(0, styl.ODSTEP_MALY))

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
        self._menu_magazyn.grid(row=0, column=1)

        ctk.CTkButton(
            pasek_naglowka,
            text="Eksportuj CSV",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._eksportuj,
        ).grid(row=0, column=3, sticky="e")

        self._tabela = Tabela(self, kolumny=KOLUMNY)
        self._tabela.grid(row=1, column=0, sticky="nsew")

    def odswiez(self) -> None:
        def zadanie():
            return api_client.pobierz_magazyny(tylko_aktywne=True, limit=200)

        def sukces(magazyny: list[dict]) -> None:
            etykiety = [WSZYSTKIE_MAGAZYNY] + [m["nazwa"] for m in magazyny]
            self._klucze_wg_etykiety_magazynu = {m["nazwa"]: m["id"] for m in magazyny}
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
            return api_client.pobierz_raport_ponizej_minimum(magazyn_id=magazyn_id)

        def sukces(stany: list[dict]) -> None:
            self._stany = stany
            formatery = {
                "ilosc": lambda s: formatowanie.formatuj_ilosc(
                    s["ilosc"], s["jednostka_miary"]
                ),
                "stan_minimalny": lambda s: formatowanie.formatuj_ilosc(
                    s["stan_minimalny"], s["jednostka_miary"]
                ),
            }
            kolory = {
                klucz: (lambda s: styl.KOLOR_OSTRZEZENIE)
                for klucz, _etykieta, _waga in KOLUMNY
            }
            self._tabela.ustaw_dane(stany, formatery=formatery, kolory=kolory)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _eksportuj(self) -> None:
        formatery = {
            "ilosc": lambda s: formatowanie.formatuj_ilosc(s["ilosc"]),
            "stan_minimalny": lambda s: formatowanie.formatuj_ilosc(s["stan_minimalny"]),
        }
        eksportuj_do_csv(
            self, self._stany, KOLUMNY_CSV, "ponizej_minimum.csv", formatery=formatery
        )
