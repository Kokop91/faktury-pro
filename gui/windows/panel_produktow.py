from decimal import Decimal

import customtkinter as ctk

from gui import api_client, formatowanie, ikony, nastawienia, styl
from gui.eksport_csv import eksportuj_do_csv
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, ustaw_tekst_ladowania
from gui.windows.dialog_importu_produktow import DialogImportuProduktow
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

# Faza 26 - eksport pelnego katalogu (nie tylko aktywnych/przefiltrowanych w
# widoku) - patrz mirror w gui/windows/widok_klientow.py:KOLUMNY_CSV_KLIENTOW.
KOLUMNY_CSV_PRODUKTOW = [
    ("nazwa", "Nazwa"),
    ("jednostka_miary", "Jednostka miary"),
    ("cena_netto_grosze", "Cena netto"),
    ("koszt_zakupu_grosze", "Koszt zakupu"),
    ("domyslna_stawka_vat", "Stawka VAT"),
    ("jest_magazynowy", "Typ"),
    ("objety_zalacznikiem_15", "Załącznik nr 15 (MPP)"),
    ("aktywny", "Aktywny"),
]

FILTR_WSZYSTKIE = "Wszystkie"
FILTR_TOWARY = "Tylko towary"
FILTR_USLUGI = "Tylko usługi"
OPCJE_FILTRA = [FILTR_WSZYSTKIE, FILTR_TOWARY, FILTR_USLUGI]

_KLUCZ_FILTR = "filtr_typ_produktow"
_KLUCZ_SORTOWANIE = "sortowanie_produkty"


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
        pasek_naglowka.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            pasek_naglowka,
            text="Typ:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=0, padx=(0, styl.ODSTEP_MALY))

        filtr_zapisany = nastawienia.wczytaj(_KLUCZ_FILTR)
        wartosc_filtra = filtr_zapisany if filtr_zapisany in OPCJE_FILTRA else FILTR_WSZYSTKIE
        self._var_filtr = ctk.StringVar(value=wartosc_filtra)
        ctk.CTkOptionMenu(
            pasek_naglowka,
            values=OPCJE_FILTRA,
            variable=self._var_filtr,
            command=lambda wartosc: self._na_zmiane_filtra(wartosc),
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=0, column=1, sticky="w")

        self._pole_szukaj = ctk.CTkEntry(
            pasek_naglowka,
            font=styl.CZCIONKA_TRESC,
            width=220,
            placeholder_text="Szukaj po nazwie...",
        )
        self._pole_szukaj.grid(row=0, column=2, padx=(styl.ODSTEP_SREDNI, styl.ODSTEP_SREDNI), sticky="w")
        self._pole_szukaj.bind("<KeyRelease>", lambda _z: self._odswiez_tabele())

        self._przycisk_eksportuj = ctk.CTkButton(
            pasek_naglowka,
            text="Eksportuj do CSV",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._eksportuj_csv,
        )
        self._przycisk_eksportuj.grid(row=0, column=3, padx=(0, styl.ODSTEP_MALY))

        ctk.CTkButton(
            pasek_naglowka,
            text="Importuj z CSV",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._otworz_import_csv,
        ).grid(row=0, column=4, padx=(0, styl.ODSTEP_MALY))

        ctk.CTkButton(
            pasek_naglowka,
            text="Dodaj produkt",
            image=ikony.ikona_stala("plus"),
            compound="left",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_formularz,
        ).grid(row=0, column=5)

        sortowanie_zapisane = nastawienia.wczytaj(_KLUCZ_SORTOWANIE)
        sortowanie_poczatkowe = (
            tuple(sortowanie_zapisane) if isinstance(sortowanie_zapisane, list) else None
        )
        self._tabela = Tabela(
            self,
            kolumny=KOLUMNY,
            on_wiersz_kliknij=self._otworz_szczegoly,
            sortowalne=True,
            sortowanie_poczatkowe=sortowanie_poczatkowe,
            on_zmiana_sortowania=lambda klucz, malejaco: nastawienia.zapisz(
                _KLUCZ_SORTOWANIE, [klucz, malejaco]
            ),
        )
        self._tabela.grid(row=1, column=0, sticky="nsew")

    def fokus_wyszukiwania(self) -> None:
        self._pole_szukaj.focus_set()

    def _na_zmiane_filtra(self, wartosc: str) -> None:
        nastawienia.zapisz(_KLUCZ_FILTR, wartosc)
        self._odswiez_tabele()

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

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _odswiez_tabele(self) -> None:
        filtr = self._var_filtr.get()
        if filtr == FILTR_TOWARY:
            wiersze = [p for p in self._produkty if p["jest_magazynowy"]]
        elif filtr == FILTR_USLUGI:
            wiersze = [p for p in self._produkty if not p["jest_magazynowy"]]
        else:
            wiersze = self._produkty

        szukana_fraza = self._pole_szukaj.get().strip().lower()
        if szukana_fraza:
            wiersze = [p for p in wiersze if szukana_fraza in p["nazwa"].lower()]

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
        klucze_sortowania = {
            "typ": lambda p: p["jest_magazynowy"],
            "stan": lambda p: self._ilosc_wg_produktu.get(p["id"], Decimal("0")),
        }
        self._tabela.ustaw_dane(
            wiersze, formatery=formatery, kolory=kolory, klucze_sortowania=klucze_sortowania
        )

    def _tekst_stanu(self, produkt: dict) -> str:
        if not produkt["jest_magazynowy"]:
            return "—"
        ilosc = self._ilosc_wg_produktu.get(produkt["id"], Decimal("0"))
        return formatowanie.formatuj_ilosc(ilosc, produkt["jednostka_miary"])

    def _otworz_formularz(self) -> None:
        FormularzProduktu(self, on_zapisano=self.odswiez)

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        SzczegolyProduktu(self, produkt_id=wiersz["id"])

    def _otworz_import_csv(self) -> None:
        DialogImportuProduktow(self, on_zaimportowano=self.odswiez)

    def _eksportuj_csv(self) -> None:
        ustaw_tekst_ladowania(self._przycisk_eksportuj, True, "Eksportuj do CSV", "Wczytywanie...")

        def zadanie():
            return _pobierz_wszystkie_produkty()

        def sukces(produkty: list[dict]) -> None:
            ustaw_tekst_ladowania(self._przycisk_eksportuj, False, "Eksportuj do CSV")
            formatery = {
                "cena_netto_grosze": lambda p: formatowanie.grosze_do_wpisu(p["cena_netto_grosze"]),
                "koszt_zakupu_grosze": lambda p: (
                    formatowanie.grosze_do_wpisu(p["koszt_zakupu_grosze"])
                    if p["koszt_zakupu_grosze"] is not None
                    else ""
                ),
                "domyslna_stawka_vat": lambda p: formatowanie.ETYKIETY_STAWEK_VAT.get(
                    p["domyslna_stawka_vat"], p["domyslna_stawka_vat"]
                ),
                "jest_magazynowy": lambda p: "Towar" if p["jest_magazynowy"] else "Usługa",
                "objety_zalacznikiem_15": lambda p: "Tak" if p["objety_zalacznikiem_15"] else "Nie",
                "aktywny": lambda p: "Tak" if p["aktywny"] else "Nie",
            }
            eksportuj_do_csv(
                self, produkty, KOLUMNY_CSV_PRODUKTOW, "produkty.csv", formatery=formatery
            )

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_eksportuj, False, "Eksportuj do CSV")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)


def _pobierz_wszystkie_produkty() -> list[dict]:
    """Mirror gui/windows/widok_klientow.py:_pobierz_wszystkich_klientow -
    eksport CSV ma objac caly katalog, nie tylko strone widoczna w panelu."""
    wszystkie: list[dict] = []
    skip = 0
    while True:
        strona = api_client.pobierz_produkty(tylko_aktywne=False, skip=skip, limit=200)
        wszystkie.extend(strona)
        if len(strona) < 200:
            return wszystkie
        skip += 200
