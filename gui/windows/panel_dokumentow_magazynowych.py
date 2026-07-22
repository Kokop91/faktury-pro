import customtkinter as ctk

from gui import api_client, formatowanie, ikony, nastawienia, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_dokumentu_magazynowego import FormularzDokumentuMagazynowego
from gui.windows.szczegoly_dokumentu_magazynowego import SzczegolyDokumentuMagazynowego
from gui.windows.tabela import Tabela

_KLUCZ_FILTR = "filtr_dokumenty_magazynowe"

KOLUMNY = [
    ("numer", "Numer", 2),
    ("typ", "Typ", 2),
    ("status", "Status", 1),
    ("data_dokumentu", "Data", 1),
    ("zrodlowy", "Magazyn źródłowy", 2),
    ("docelowy", "Magazyn docelowy", 2),
]

WSZYSTKIE_TYPY = "Wszystkie typy"
_ETYKIETY_TYPOW = [WSZYSTKIE_TYPY] + [
    formatowanie.ETYKIETY_TYPU_DOKUMENTU_MAGAZYNOWEGO[t]
    for t in formatowanie.KOLEJNOSC_TYPOW_DOKUMENTU_MAGAZYNOWEGO
]
_KLUCZE_WG_ETYKIETY_TYPU = {WSZYSTKIE_TYPY: None, **{
    formatowanie.ETYKIETY_TYPU_DOKUMENTU_MAGAZYNOWEGO[t]: t
    for t in formatowanie.KOLEJNOSC_TYPOW_DOKUMENTU_MAGAZYNOWEGO
}}


class PanelDokumentowMagazynowych(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._magazyny_wg_id: dict[int, str] = {}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI)
        )

        ctk.CTkLabel(
            pasek_naglowka,
            text="Typ:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).pack(side="left", padx=(0, styl.ODSTEP_MALY))

        filtr_zapisany = nastawienia.wczytaj(_KLUCZ_FILTR) or {}

        self._var_typ = ctk.StringVar(
            value=filtr_zapisany.get("typ") if filtr_zapisany.get("typ") in _ETYKIETY_TYPOW else WSZYSTKIE_TYPY
        )
        ctk.CTkOptionMenu(
            pasek_naglowka,
            values=_ETYKIETY_TYPOW,
            variable=self._var_typ,
            command=lambda _wartosc: self.odswiez(),
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(side="left", padx=(0, styl.ODSTEP_SREDNI))

        ctk.CTkLabel(
            pasek_naglowka,
            text="Od:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).pack(side="left", padx=(0, styl.ODSTEP_MALY))
        self._pole_data_od = ctk.CTkEntry(
            pasek_naglowka, font=styl.CZCIONKA_TRESC, width=110,
            placeholder_text="DD.MM.RRRR",
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
            pasek_naglowka, font=styl.CZCIONKA_TRESC, width=110,
            placeholder_text="DD.MM.RRRR",
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
            command=self.odswiez,
        ).pack(side="left")

        ctk.CTkButton(
            pasek_naglowka,
            text="Nowy dokument",
            image=ikony.ikona_stala("plus"),
            compound="left",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_formularz,
        ).pack(side="right")

        self._tabela = Tabela(
            self, kolumny=KOLUMNY, on_wiersz_kliknij=self._otworz_szczegoly
        )
        self._tabela.grid(row=1, column=0, sticky="nsew")

    def odswiez(self) -> None:
        typ = _KLUCZE_WG_ETYKIETY_TYPU.get(self._var_typ.get())

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
            {"typ": self._var_typ.get(), "data_od": tekst_od, "data_do": tekst_do},
        )

        def zadanie():
            magazyny = api_client.pobierz_magazyny(tylko_aktywne=False, limit=200)
            dokumenty = api_client.pobierz_dokumenty_magazynowe(
                typ=typ, data_od=data_od, data_do=data_do, limit=200
            )
            return magazyny, dokumenty

        def sukces(wynik) -> None:
            magazyny, dokumenty = wynik
            self._magazyny_wg_id = {m["id"]: m["nazwa"] for m in magazyny}

            formatery = {
                "typ": lambda d: formatowanie.formatuj_typ_dokumentu_magazynowego(
                    d["typ"]
                ),
                "status": lambda d: formatowanie.formatuj_status_dokumentu_magazynowego(
                    d["status"]
                ),
                "data_dokumentu": lambda d: formatowanie.formatuj_date(
                    d["data_dokumentu"]
                ),
                "zrodlowy": lambda d: (
                    self._magazyny_wg_id.get(d["magazyn_zrodlowy_id"], "—")
                    if d.get("magazyn_zrodlowy_id")
                    else "—"
                ),
                "docelowy": lambda d: (
                    self._magazyny_wg_id.get(d["magazyn_docelowy_id"], "—")
                    if d.get("magazyn_docelowy_id")
                    else "—"
                ),
            }
            kolory = {
                "status": lambda d: formatowanie.kolor_statusu_dokumentu_magazynowego(
                    d["status"]
                ),
            }
            self._tabela.ustaw_dane(dokumenty, formatery=formatery, kolory=kolory)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _otworz_formularz(self) -> None:
        FormularzDokumentuMagazynowego(self, on_zapisano=self.odswiez)

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        SzczegolyDokumentuMagazynowego(
            self, dokument_id=wiersz["id"], on_zmieniono=self.odswiez
        )
