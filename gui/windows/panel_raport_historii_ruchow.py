from decimal import Decimal

import customtkinter as ctk

from gui import api_client, formatowanie, nastawienia, styl
from gui.eksport_csv import eksportuj_do_csv
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.tabela import Tabela

_KLUCZ_FILTR = "filtr_historia_ruchow"

KOLUMNY = [
    ("data_dokumentu", "Data", 1),
    ("dokument", "Dokument", 2),
    ("produkt_nazwa", "Produkt", 2),
    ("magazyn_nazwa", "Magazyn", 2),
    ("zmiana_ilosci", "Zmiana ilości", 1),
    ("notatka", "Notatka", 2),
]

KOLUMNY_CSV = [
    ("data_dokumentu", "Data"),
    ("typ_dokumentu", "Typ dokumentu"),
    ("numer_dokumentu", "Numer dokumentu"),
    ("produkt_nazwa", "Produkt"),
    ("magazyn_nazwa", "Magazyn"),
    ("zmiana_ilosci", "Zmiana ilości"),
    ("notatka", "Notatka"),
]

WSZYSTKIE_MAGAZYNY = "Wszystkie magazyny"


class PanelRaportHistoriiRuchow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._klucze_wg_etykiety_magazynu: dict[str, int] = {}
        self._ruchy: list[dict] = []
        self._filtr_przywrocony = False
        filtr_zapisany = nastawienia.wczytaj(_KLUCZ_FILTR) or {}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(row=0, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI))

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
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        )
        self._menu_magazyn.pack(side="left", padx=(0, styl.ODSTEP_SREDNI))

        ctk.CTkLabel(
            pasek_naglowka,
            text="Od:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).pack(side="left", padx=(0, styl.ODSTEP_MALY))
        self._pole_data_od = ctk.CTkEntry(
            pasek_naglowka, font=styl.CZCIONKA_TRESC, width=110, placeholder_text="DD.MM.RRRR"
        )
        self._pole_data_od.insert(0, filtr_zapisany.get("data_od", ""))
        self._pole_data_od.pack(side="left", padx=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            pasek_naglowka,
            text="Do:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).pack(side="left", padx=(0, styl.ODSTEP_MALY))
        self._pole_data_do = ctk.CTkEntry(
            pasek_naglowka, font=styl.CZCIONKA_TRESC, width=110, placeholder_text="DD.MM.RRRR"
        )
        self._pole_data_do.insert(0, filtr_zapisany.get("data_do", ""))
        self._pole_data_do.pack(side="left", padx=(0, styl.ODSTEP_SREDNI))

        ctk.CTkButton(
            pasek_naglowka,
            text="Filtruj",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._odswiez_ruchy,
        ).pack(side="left", padx=(0, styl.ODSTEP_MALY))

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
        ).pack(side="right")

        self._tabela = Tabela(self, kolumny=KOLUMNY)
        self._tabela.grid(row=1, column=0, sticky="nsew")

    def odswiez(self) -> None:
        def zadanie():
            return api_client.pobierz_magazyny(tylko_aktywne=True, limit=200)

        def sukces(magazyny: list[dict]) -> None:
            etykiety = [WSZYSTKIE_MAGAZYNY] + [m["nazwa"] for m in magazyny]
            self._klucze_wg_etykiety_magazynu = {m["nazwa"]: m["id"] for m in magazyny}
            self._menu_magazyn.configure(values=etykiety)
            if not self._filtr_przywrocony:
                self._filtr_przywrocony = True
                zapisany = (nastawienia.wczytaj(_KLUCZ_FILTR) or {}).get("magazyn")
                if zapisany in etykiety:
                    self._var_magazyn.set(zapisany)
            elif self._var_magazyn.get() not in etykiety:
                self._var_magazyn.set(WSZYSTKIE_MAGAZYNY)
            self._odswiez_ruchy()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _odswiez_ruchy(self) -> None:
        magazyn_id = self._klucze_wg_etykiety_magazynu.get(self._var_magazyn.get())

        data_od = None
        tekst_od = self._pole_data_od.get().strip()
        if tekst_od:
            try:
                data_od = formatowanie.parsuj_date_pl(tekst_od).isoformat()
            except ValueError as e:
                komunikat_bledu(self, f"Data od: {e}")
                return

        data_do = None
        tekst_do = self._pole_data_do.get().strip()
        if tekst_do:
            try:
                data_do = formatowanie.parsuj_date_pl(tekst_do).isoformat()
            except ValueError as e:
                komunikat_bledu(self, f"Data do: {e}")
                return

        nastawienia.zapisz(
            _KLUCZ_FILTR,
            {"magazyn": self._var_magazyn.get(), "data_od": tekst_od, "data_do": tekst_do},
        )

        def zadanie():
            return api_client.pobierz_raport_historii_ruchow(
                magazyn_id=magazyn_id, data_od=data_od, data_do=data_do
            )

        def sukces(ruchy: list[dict]) -> None:
            self._ruchy = ruchy
            formatery = {
                "data_dokumentu": lambda r: formatowanie.formatuj_date(r["data_dokumentu"]),
                "dokument": lambda r: (
                    f"{formatowanie.formatuj_typ_dokumentu_magazynowego(r['typ_dokumentu'])} "
                    f"— {r['numer_dokumentu']}"
                ),
                "zmiana_ilosci": lambda r: (
                    ("+" if Decimal(str(r["zmiana_ilosci"])) > 0 else "")
                    + formatowanie.formatuj_ilosc(r["zmiana_ilosci"])
                ),
                "notatka": lambda r: r.get("notatka") or "",
            }
            kolory = {
                "zmiana_ilosci": lambda r: (
                    styl.KOLOR_SUKCES
                    if Decimal(str(r["zmiana_ilosci"])) > 0
                    else styl.KOLOR_BLAD
                ),
            }
            self._tabela.ustaw_dane(ruchy, formatery=formatery, kolory=kolory)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _eksportuj(self) -> None:
        formatery = {
            "zmiana_ilosci": lambda r: formatowanie.formatuj_ilosc(r["zmiana_ilosci"]),
            "notatka": lambda r: r.get("notatka") or "",
        }
        eksportuj_do_csv(
            self, self._ruchy, KOLUMNY_CSV, "historia_ruchow.csv", formatery=formatery
        )
