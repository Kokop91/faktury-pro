from decimal import Decimal

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_produktu import FormularzProduktu
from gui.windows.szczegoly_produktu import SzczegolyProduktu
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("nazwa", "Nazwa", 3),
    ("jednostka_miary", "J.m.", 1),
    ("cena_netto_grosze", "Cena netto", 2),
    ("typ", "Typ", 1),
    ("stan", "Stan", 2),
]

FILTR_WSZYSTKIE = "Wszystkie"
FILTR_TOWARY = "Tylko towary"
FILTR_USLUGI = "Tylko usługi"
OPCJE_FILTRA = [FILTR_WSZYSTKIE, FILTR_TOWARY, FILTR_USLUGI]


class PanelProduktow(ctk.CTkFrame):
    """Stan magazynowy pokazany tu jako SUMA ze wszystkich magazynow (jedna
    liczba) - to jest ogolny katalog produktow/uslug, wiec ma sens przeglad
    "ile mam tego lacznie". Rozbicie stanu per magazyn jest w osobnej zakladce
    "Stany magazynowe" (z filtrem po magazynie) - tam jest wlasciwe miejsce na
    operacyjny szczegol, tutaj wystarczy sygnal "ile" i "czy ponizej minimum
    gdziekolwiek", zeby nie duplikowac tej samej tabeli w dwoch miejscach.
    """

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._produkty: list[dict] = []
        self._ilosc_wg_produktu: dict[int, Decimal] = {}
        self._ponizej_minimum_wg_produktu: dict[int, bool] = {}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI)
        )
        pasek_naglowka.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            pasek_naglowka,
            text="Typ:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=0, padx=(0, styl.ODSTEP_MALY))

        self._var_filtr = ctk.StringVar(value=FILTR_WSZYSTKIE)
        ctk.CTkOptionMenu(
            pasek_naglowka,
            values=OPCJE_FILTRA,
            variable=self._var_filtr,
            command=lambda _wartosc: self._odswiez_tabele(),
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkButton(
            pasek_naglowka,
            text="+ Dodaj produkt",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_formularz,
        ).grid(row=0, column=2)

        self._tabela = Tabela(
            self, kolumny=KOLUMNY, on_wiersz_kliknij=self._otworz_szczegoly
        )
        self._tabela.grid(row=1, column=0, sticky="nsew")

    def odswiez(self) -> None:
        def zadanie():
            produkty = api_client.pobierz_produkty(tylko_aktywne=True, limit=200)
            stany = api_client.pobierz_stany_magazynowe()
            return produkty, stany

        def sukces(wynik) -> None:
            produkty, stany = wynik
            self._produkty = produkty

            self._ilosc_wg_produktu = {}
            self._ponizej_minimum_wg_produktu = {}
            for stan in stany:
                produkt_id = stan["produkt_id"]
                self._ilosc_wg_produktu[produkt_id] = self._ilosc_wg_produktu.get(
                    produkt_id, Decimal("0")
                ) + Decimal(str(stan["ilosc"]))
                if stan["ponizej_minimum"]:
                    self._ponizej_minimum_wg_produktu[produkt_id] = True

            self._odswiez_tabele()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _odswiez_tabele(self) -> None:
        filtr = self._var_filtr.get()
        if filtr == FILTR_TOWARY:
            wiersze = [p for p in self._produkty if p["jest_magazynowy"]]
        elif filtr == FILTR_USLUGI:
            wiersze = [p for p in self._produkty if not p["jest_magazynowy"]]
        else:
            wiersze = self._produkty

        formatery = {
            "cena_netto_grosze": lambda p: formatowanie.formatuj_kwote(
                p["cena_netto_grosze"]
            ),
            "typ": lambda p: "Towar" if p["jest_magazynowy"] else "Usługa",
            "stan": self._tekst_stanu,
        }
        kolory = {
            "stan": lambda p: (
                styl.KOLOR_OSTRZEZENIE
                if self._ponizej_minimum_wg_produktu.get(p["id"])
                else styl.KOLOR_TEKST_GLOWNY
            ),
        }
        self._tabela.ustaw_dane(wiersze, formatery=formatery, kolory=kolory)

    def _tekst_stanu(self, produkt: dict) -> str:
        if not produkt["jest_magazynowy"]:
            return "—"
        ilosc = self._ilosc_wg_produktu.get(produkt["id"], Decimal("0"))
        return formatowanie.formatuj_ilosc(ilosc, produkt["jednostka_miary"])

    def _otworz_formularz(self) -> None:
        FormularzProduktu(self, on_zapisano=self.odswiez)

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        SzczegolyProduktu(self, produkt_id=wiersz["id"])
