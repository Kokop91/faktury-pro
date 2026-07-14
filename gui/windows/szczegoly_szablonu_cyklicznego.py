from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.formularz_szablonu_cyklicznego import FormularzSzablonuCyklicznego
from gui.windows.tabela import Tabela

KOLUMNY_POZYCJI = [
    ("nazwa", "Nazwa", 3),
    ("ilosc", "Ilość", 1),
    ("jednostka_miary", "J.m.", 1),
    ("cena_netto_grosze", "Cena netto", 2),
    ("stawka_vat", "VAT", 1),
]

KOLUMNY_HISTORII = [
    ("numer", "Numer", 2),
    ("okres_cykliczny", "Okres", 2),
    ("data_wystawienia", "Data wystawienia", 2),
    ("status", "Status", 2),
    ("kwota_brutto", "Kwota brutto", 2),
]

ETYKIETY_STAWEK_VAT = {"23": "23%", "8": "8%", "5": "5%", "0": "0%", "zw": "zw."}


class SzczegolySzablonuCyklicznego(OknoFormularza):
    def __init__(
        self,
        master,
        szablon_id: int,
        on_zmiana: Callable[[], None] | None = None,
    ):
        super().__init__(master)
        self.title("Szczegóły szablonu cyklicznego")
        self.geometry("820x780")

        self._szablon_id = szablon_id
        self._szablon: dict | None = None
        self._on_zmiana = on_zmiana or (lambda: None)

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        self._zaladuj()

    def _zaladuj(self) -> None:
        def zadanie():
            szablon = api_client.pobierz_szablon_cykliczny(self._szablon_id)
            klient = api_client.pobierz_klienta(szablon["klient_id"])
            historia = api_client.historia_faktur_szablonu(self._szablon_id)
            return szablon, klient["nazwa"], historia

        def sukces(wynik) -> None:
            szablon, nazwa_klienta, historia = wynik
            self._szablon = szablon
            self._nazwa_klienta = nazwa_klienta
            self._historia = historia
            self._etykieta_ladowania.destroy()
            self._zbuduj_widok(szablon)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            self.destroy()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_widok(self, szablon: dict) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(5, weight=1)

        naglowek = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        naglowek.grid(
            row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        ctk.CTkLabel(
            naglowek,
            text=f"{formatowanie.formatuj_typ_dokumentu(szablon['typ_dokumentu'])} — {self._nazwa_klienta}",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(anchor="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        wiersze_info = [
            (
                "Status",
                formatowanie.formatuj_status_szablonu(szablon["status"]),
                formatowanie.kolor_statusu_szablonu(szablon["status"]),
            ),
            ("Częstotliwość", formatowanie.formatuj_czestotliwosc(szablon["czestotliwosc"]), None),
            ("Dzień generowania", str(szablon["dzien_generowania"]), None),
            ("Data początku", formatowanie.formatuj_date(szablon["data_poczatku"]), None),
            (
                "Data zakończenia",
                formatowanie.formatuj_date(szablon["data_konca"]) if szablon.get("data_konca") else "—",
                None,
            ),
            (
                "Następny termin",
                formatowanie.formatuj_date(szablon["nastepny_termin"]) if szablon.get("nastepny_termin") else "—",
                None,
            ),
            ("Waluta", szablon["waluta"], None),
        ]
        for etykieta, wartosc, kolor in wiersze_info:
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
                font=styl.CZCIONKA_TRESC_POGRUBIONA if kolor else styl.CZCIONKA_TRESC,
                text_color=kolor or styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
            ).pack(side="left")
        ctk.CTkFrame(naglowek, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        ctk.CTkLabel(
            self, text="Pozycje", font=styl.NAGLOWEK_2, text_color=styl.KOLOR_TEKST_GLOWNY
        ).grid(row=1, column=0, sticky="w", padx=styl.ODSTEP_DUZY)

        tabela_pozycji = Tabela(self, kolumny=KOLUMNY_POZYCJI, height=140)
        tabela_pozycji.grid(
            row=2, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_MALY, styl.ODSTEP_MALY)
        )
        formatery_pozycji = {
            "cena_netto_grosze": lambda p: formatowanie.formatuj_kwote(
                p["cena_netto_grosze"], szablon["waluta"]
            ),
            "stawka_vat": lambda p: ETYKIETY_STAWEK_VAT.get(p["stawka_vat"], p["stawka_vat"]),
        }
        tabela_pozycji.ustaw_dane(szablon["pozycje"], formatery=formatery_pozycji)

        pasek_akcji = ctk.CTkFrame(self, fg_color="transparent")
        pasek_akcji.grid(
            row=3, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
        )

        ctk.CTkButton(
            pasek_akcji,
            text="Edytuj",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._edytuj,
        ).pack(side="left", padx=(0, styl.ODSTEP_MALY))

        aktywny = szablon["status"] == "aktywny"
        self._przycisk_status = ctk.CTkButton(
            pasek_akcji,
            text="Wstrzymaj szablon" if aktywny else "Wznów szablon",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_OSTRZEZENIE if aktywny else styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._przelacz_status,
        )
        self._przycisk_status.pack(side="left")

        ctk.CTkLabel(
            self,
            text="Historia wygenerowanych faktur",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=4, column=0, sticky="w", padx=styl.ODSTEP_DUZY)

        tabela_historii = Tabela(
            self, kolumny=KOLUMNY_HISTORII, on_wiersz_kliknij=self._otworz_fakture
        )
        tabela_historii.grid(
            row=5, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_MALY, styl.ODSTEP_DUZY)
        )
        formatery_historii = {
            "okres_cykliczny": lambda f: formatowanie.formatuj_date(f["okres_cykliczny"]),
            "data_wystawienia": lambda f: formatowanie.formatuj_date(f["data_wystawienia"]),
            "status": lambda f: formatowanie.formatuj_status(f["status_efektywny"]),
            "kwota_brutto": lambda f: formatowanie.formatuj_kwote(
                f["suma_brutto_grosze"], f["waluta"]
            ),
        }
        kolory_historii = {
            "status": lambda f: formatowanie.kolor_statusu(f["status_efektywny"]),
        }
        tabela_historii.ustaw_dane(
            self._historia, formatery=formatery_historii, kolory=kolory_historii
        )

    def _edytuj(self) -> None:
        FormularzSzablonuCyklicznego(self, on_zapisano=self._po_edycji, szablon=self._szablon)

    def _po_edycji(self) -> None:
        self._on_zmiana()
        self._odswiez_w_miejscu()

    def _odswiez_w_miejscu(self) -> None:
        szablon_id = self._szablon_id
        on_zmiana = self._on_zmiana
        master = self.master
        self.destroy()
        SzczegolySzablonuCyklicznego(master, szablon_id=szablon_id, on_zmiana=on_zmiana)

    def _przelacz_status(self) -> None:
        nowy_status = "wstrzymany" if self._szablon["status"] == "aktywny" else "aktywny"
        ustaw_tekst_ladowania(
            self._przycisk_status, True,
            "Wstrzymaj szablon" if nowy_status == "wstrzymany" else "Wznów szablon",
        )

        def zadanie():
            return api_client.zmien_status_szablonu_cyklicznego(self._szablon_id, nowy_status)

        def sukces(_wynik) -> None:
            self._on_zmiana()
            master = self.master
            tekst = "wstrzymany" if nowy_status == "wstrzymany" else "wznowiony"
            self._odswiez_w_miejscu()
            pokaz_toast(master, f"Szablon cykliczny {tekst}.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(
                self._przycisk_status, False,
                "Wstrzymaj szablon" if self._szablon["status"] == "aktywny" else "Wznów szablon",
            )
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _otworz_fakture(self, wiersz: dict) -> None:
        from gui.windows.szczegoly_faktury import SzczegolyFaktury

        SzczegolyFaktury(
            self,
            faktura_id=wiersz["id"],
            nazwa_klienta=self._nazwa_klienta,
            on_zmiana=self._po_edycji,
        )
