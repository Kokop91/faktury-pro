from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, pokaz_toast
from gui.windows.baza_formularza import OknoFormularza


class SzczegolyDokumentuKosztowego(OknoFormularza):
    def __init__(self, master, dokument_id: int, on_zmiana: Callable[[], None] | None = None):
        super().__init__(master)
        self.title("Szczegóły dokumentu kosztowego")
        self.geometry("700x680")

        self._dokument_id = dokument_id
        self._dokument: dict | None = None
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
            return api_client.pobierz_dokument_kosztowy(self._dokument_id)

        def sukces(dokument: dict) -> None:
            self._dokument = dokument
            self._etykieta_ladowania.destroy()
            self._zbuduj_widok(dokument)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            self.destroy()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_widok(self, dokument: dict) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        naglowek = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        naglowek.grid(
            row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        tytul = dokument.get("kontrahent_nazwa") or f"NIP {dokument.get('kontrahent_nip') or '?'}"
        ctk.CTkLabel(
            naglowek,
            text=f"{tytul} — {dokument['numer_faktury']}",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            wraplength=620,
            justify="left",
        ).pack(anchor="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        wiersze_info = [
            (
                "Status",
                formatowanie.formatuj_status_dokumentu_kosztowego(dokument["status"]),
                formatowanie.kolor_statusu_dokumentu_kosztowego(dokument["status"]),
            ),
            ("Kontrahent (NIP)", dokument.get("kontrahent_nip") or "—", None),
            ("Numer KSeF", dokument["numer_ksef"], None),
            ("Data wystawienia", formatowanie.formatuj_date(dokument["data_wystawienia"]), None),
            ("Kwota netto", formatowanie.formatuj_kwote(dokument["netto_grosze"], dokument["waluta"]), None),
            (
                "Kwota VAT (PLN)",
                formatowanie.formatuj_kwote(dokument["vat_grosze_pln"], "PLN"),
                None,
            ),
            ("Kwota brutto", formatowanie.formatuj_kwote(dokument["brutto_grosze"], dokument["waluta"]), None),
            ("Pobrano", formatowanie.formatuj_data_czas(dokument["pobrano_o"]), None),
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
                wraplength=440,
                justify="left",
            ).pack(side="left")

        ctk.CTkFrame(naglowek, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        pasek_akcji = ctk.CTkFrame(self, fg_color="transparent")
        pasek_akcji.grid(row=1, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk_akceptuj = ctk.CTkButton(
            pasek_akcji,
            text="Oznacz jako zaakceptowana",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            state="disabled" if dokument["status"] == "zaakceptowana" else "normal",
            command=lambda: self._zmien_status("zaakceptowana"),
        )
        self._przycisk_akceptuj.pack(side="left", padx=(0, styl.ODSTEP_MALY))

        self._przycisk_wyjasnienia = ctk.CTkButton(
            pasek_akcji,
            text="Oznacz jako do wyjaśnienia",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            state="disabled" if dokument["status"] == "do_wyjasnienia" else "normal",
            command=lambda: self._zmien_status("do_wyjasnienia"),
        )
        self._przycisk_wyjasnienia.pack(side="left")

        ctk.CTkLabel(
            self,
            text="Oryginalny dokument XML (z KSeF)",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=2, column=0, sticky="nw", padx=styl.ODSTEP_DUZY)

        ramka_xml = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        ramka_xml.grid(
            row=3, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_MALY, styl.ODSTEP_DUZY)
        )
        self.grid_rowconfigure(3, weight=1)
        ramka_xml.grid_columnconfigure(0, weight=1)
        ramka_xml.grid_rowconfigure(0, weight=1)

        pole_xml = ctk.CTkTextbox(
            ramka_xml,
            font=("Consolas", 11),
            fg_color="transparent",
            text_color=styl.KOLOR_TEKST_GLOWNY,
            wrap="none",
        )
        pole_xml.grid(row=0, column=0, sticky="nsew", padx=styl.ODSTEP_MALY, pady=styl.ODSTEP_MALY)
        pole_xml.insert("1.0", dokument["xml_oryginalny"])
        pole_xml.configure(state="disabled")

    def _zmien_status(self, nowy_status: str) -> None:
        self._przycisk_akceptuj.configure(state="disabled")
        self._przycisk_wyjasnienia.configure(state="disabled")

        def zadanie():
            return api_client.zmien_status_dokumentu_kosztowego(self._dokument_id, nowy_status)

        def sukces(dokument: dict) -> None:
            self._dokument = dokument
            self._przycisk_akceptuj.configure(
                state="disabled" if dokument["status"] == "zaakceptowana" else "normal"
            )
            self._przycisk_wyjasnienia.configure(
                state="disabled" if dokument["status"] == "do_wyjasnienia" else "normal"
            )
            pokaz_toast(self, "Status dokumentu zaktualizowany.")
            self._on_zmiana()

        def blad(e: api_client.ApiError) -> None:
            self._przycisk_akceptuj.configure(
                state="disabled" if self._dokument["status"] == "zaakceptowana" else "normal"
            )
            self._przycisk_wyjasnienia.configure(
                state="disabled" if self._dokument["status"] == "do_wyjasnienia" else "normal"
            )
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
