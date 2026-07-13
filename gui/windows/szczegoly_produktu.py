from decimal import Decimal

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.tabela import Tabela

KOLUMNY_HISTORII = [
    ("data_dokumentu", "Data", 2),
    ("dokument", "Dokument", 2),
    ("magazyn_nazwa", "Magazyn", 2),
    ("zmiana_ilosci", "Zmiana ilości", 2),
    ("notatka", "Notatka", 3),
]


class SzczegolyProduktu(ctk.CTkToplevel):
    def __init__(self, master, produkt_id: int):
        super().__init__(master)
        self.title("Szczegóły produktu")
        self.geometry("760x640")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()

        self._produkt_id = produkt_id

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        self._zaladuj(produkt_id)

    def _zaladuj(self, produkt_id: int) -> None:
        def zadanie():
            produkt = api_client.pobierz_produkt(produkt_id)
            historia = (
                api_client.pobierz_historie_ruchow_produktu(produkt_id)
                if produkt["jest_magazynowy"]
                else []
            )
            return produkt, historia

        def sukces(wynik) -> None:
            produkt, historia = wynik
            self._etykieta_ladowania.destroy()
            self._zbuduj_widok(produkt, historia)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            self.destroy()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_widok(self, produkt: dict, historia: list[dict]) -> None:
        self.grid_columnconfigure(0, weight=1)

        naglowek = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        naglowek.grid(
            row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        ctk.CTkLabel(
            naglowek,
            text=produkt["nazwa"],
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(anchor="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        typ_tekst = "Towar magazynowy" if produkt["jest_magazynowy"] else "Usługa"
        wiersze_info = [
            ("Typ", typ_tekst),
            ("Jednostka miary", produkt["jednostka_miary"]),
            ("Cena netto", formatowanie.formatuj_kwote(produkt["cena_netto_grosze"])),
            (
                "Domyślna stawka VAT",
                formatowanie.ETYKIETY_STAWEK_VAT.get(
                    produkt["domyslna_stawka_vat"], produkt["domyslna_stawka_vat"]
                ),
            ),
            ("Aktywny", "Tak" if produkt["aktywny"] else "Nie"),
        ]
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

        if not produkt["jest_magazynowy"]:
            self.grid_rowconfigure(0, weight=1)
            ctk.CTkLabel(
                self,
                text="Usługi nie mają stanu magazynowego ani historii ruchów.",
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            ).grid(row=1, column=0, pady=(0, styl.ODSTEP_DUZY))
            return

        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self,
            text="Historia ruchów",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=1, column=0, sticky="w", padx=styl.ODSTEP_DUZY)

        tabela = Tabela(self, kolumny=KOLUMNY_HISTORII)
        tabela.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_MALY, styl.ODSTEP_DUZY),
        )
        formatery = {
            "data_dokumentu": lambda r: formatowanie.formatuj_date(
                r["data_dokumentu"]
            ),
            "dokument": lambda r: (
                f"{formatowanie.formatuj_typ_dokumentu_magazynowego(r['typ_dokumentu'])} "
                f"— {r['numer_dokumentu']}"
            ),
            "zmiana_ilosci": lambda r: (
                ("+" if Decimal(str(r["zmiana_ilosci"])) > 0 else "")
                + formatowanie.formatuj_ilosc(
                    r["zmiana_ilosci"], produkt["jednostka_miary"]
                )
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
        tabela.ustaw_dane(historia, formatery=formatery, kolory=kolory)
