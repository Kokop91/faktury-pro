import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.tabela import Tabela

KOLUMNY_POZYCJI = [
    ("produkt", "Produkt", 3),
    ("ilosc", "Ilość", 1),
    ("notatka", "Notatka", 3),
]


class SzczegolyDokumentuMagazynowego(OknoFormularza):
    """Wylacznie do odczytu - backend (Faza 8) nie ma edycji/anulowania
    dokumentow magazynowych."""

    def __init__(self, master, dokument_id: int):
        super().__init__(master)
        self.title("Szczegóły dokumentu magazynowego")
        self.geometry("700x600")

        self._dokument_id = dokument_id

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        self._zaladuj(dokument_id)

    def _zaladuj(self, dokument_id: int) -> None:
        def zadanie():
            dokument = api_client.pobierz_dokument_magazynowy(dokument_id)
            magazyny = api_client.pobierz_magazyny(tylko_aktywne=False, limit=200)
            produkty = api_client.pobierz_produkty(tylko_aktywne=False, limit=200)
            faktura_numer = None
            if dokument.get("faktura_powiazana_id"):
                faktura = api_client.pobierz_fakture(dokument["faktura_powiazana_id"])
                faktura_numer = faktura["numer"]
            return dokument, magazyny, produkty, faktura_numer

        def sukces(wynik) -> None:
            dokument, magazyny, produkty, faktura_numer = wynik
            self._etykieta_ladowania.destroy()
            self._zbuduj_widok(dokument, magazyny, produkty, faktura_numer)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            self.destroy()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_widok(
        self,
        dokument: dict,
        magazyny: list[dict],
        produkty: list[dict],
        faktura_numer: str | None,
    ) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        magazyny_wg_id = {m["id"]: m["nazwa"] for m in magazyny}
        produkty_wg_id = {p["id"]: p for p in produkty}

        naglowek = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        naglowek.grid(
            row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        tytul_tekst = (
            f"{formatowanie.formatuj_typ_dokumentu_magazynowego(dokument['typ'])} "
            f"— {dokument['numer']}"
        )
        ctk.CTkLabel(
            naglowek,
            text=tytul_tekst,
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(anchor="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        wiersze_info = [
            ("Data dokumentu", formatowanie.formatuj_date(dokument["data_dokumentu"])),
        ]
        if dokument.get("magazyn_zrodlowy_id"):
            wiersze_info.append(
                ("Magazyn źródłowy", magazyny_wg_id.get(dokument["magazyn_zrodlowy_id"], "—"))
            )
        if dokument.get("magazyn_docelowy_id"):
            wiersze_info.append(
                ("Magazyn docelowy", magazyny_wg_id.get(dokument["magazyn_docelowy_id"], "—"))
            )
        if faktura_numer:
            wiersze_info.append(("Powiązana faktura", faktura_numer))

        for etykieta, wartosc in wiersze_info:
            wiersz = ctk.CTkFrame(naglowek, fg_color="transparent")
            wiersz.pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=2)
            ctk.CTkLabel(
                wiersz,
                text=f"{etykieta}:",
                font=styl.CZCIONKA_ETYKIETA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                width=160,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                wiersz,
                text=wartosc,
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
            ).pack(side="left")
        ctk.CTkFrame(naglowek, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        ctk.CTkLabel(
            self,
            text="Pozycje",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=1, column=0, sticky="w", padx=styl.ODSTEP_DUZY)

        tabela = Tabela(self, kolumny=KOLUMNY_POZYCJI)
        tabela.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_MALY, styl.ODSTEP_DUZY),
        )
        formatery = {
            "produkt": lambda p: (
                produkty_wg_id[p["produkt_id"]]["nazwa"]
                if p["produkt_id"] in produkty_wg_id
                else f"#{p['produkt_id']}"
            ),
            "ilosc": lambda p: formatowanie.formatuj_ilosc(
                p["ilosc"],
                produkty_wg_id.get(p["produkt_id"], {}).get("jednostka_miary"),
            ),
            "notatka": lambda p: p.get("notatka") or "",
        }
        tabela.ustaw_dane(dokument["pozycje"], formatery=formatery)
