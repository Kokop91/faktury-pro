import os
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.formularz_faktury import FormularzFaktury
from gui.windows.formularz_oferty import FormularzOferty
from gui.windows.szczegoly_faktury import SzczegolyFaktury
from gui.windows.tabela import Tabela

KOLUMNY_POZYCJI = [
    ("nazwa", "Nazwa", 3),
    ("ilosc", "Ilość", 1),
    ("jednostka_miary", "J.m.", 1),
    ("cena_netto_grosze", "Cena netto", 2),
    ("stawka_vat", "VAT", 1),
    ("wartosc_netto_grosze", "Wartość netto", 2),
    ("wartosc_vat_grosze", "Kwota VAT", 2),
    ("wartosc_brutto_grosze", "Wartość brutto", 2),
]

ETYKIETY_STAWEK_VAT = {"23": "23%", "8": "8%", "5": "5%", "0": "0%", "zw": "zw."}

# Mirror app/services/oferty.py:DOZWOLONE_PRZEJSCIA_STATUSU (zduplikowane w GUI,
# osobny proces) - z jakiego stanu mozna reczne oznaczyc oferte jako
# zaakceptowana/odrzucona.
PRZEJSCIA_DOZWOLONE_Z_GUI = {
    "robocza": {"wyslana", "zaakceptowana", "odrzucona"},
    "wyslana": {"zaakceptowana", "odrzucona"},
    "zaakceptowana": set(),
    "odrzucona": set(),
}


class SzczegolyOferty(OknoFormularza):
    def __init__(
        self,
        master,
        oferta_id: int,
        nazwa_klienta: str | None = None,
        on_zmiana: Callable[[], None] | None = None,
    ):
        super().__init__(master)
        self.title("Szczegóły oferty")
        self.geometry("780x700")

        self._oferta_id = oferta_id
        self._oferta: dict | None = None
        self._nazwa_klienta = nazwa_klienta
        self._on_zmiana = on_zmiana or (lambda: None)

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        self._zaladuj(oferta_id)

    def _zaladuj(self, oferta_id: int) -> None:
        def zadanie():
            oferta = api_client.pobierz_oferte(oferta_id)
            nazwa_klienta = self._nazwa_klienta
            if nazwa_klienta is None:
                klient = api_client.pobierz_klienta(oferta["klient_id"])
                nazwa_klienta = klient["nazwa"]
            return oferta, nazwa_klienta

        def sukces(wynik) -> None:
            oferta, nazwa_klienta = wynik
            self._oferta = oferta
            self._nazwa_klienta = nazwa_klienta
            self._etykieta_ladowania.destroy()
            self._zbuduj_widok(oferta)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            self.destroy()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_widok(self, oferta: dict) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        naglowek = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        naglowek.grid(
            row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        ctk.CTkLabel(
            naglowek,
            text=f"Oferta — {oferta['numer']}",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(anchor="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        waluta_tekst = oferta["waluta"]
        if oferta["waluta"] != "PLN":
            waluta_tekst += f" (kurs {oferta['kurs_waluty']})"

        status_efektywny = oferta.get("status_efektywny", oferta["status"])
        wiersze_info = [
            ("Klient", self._nazwa_klienta or f"#{oferta['klient_id']}", None),
            (
                "Status",
                formatowanie.formatuj_status_oferty(status_efektywny),
                formatowanie.kolor_statusu_oferty(status_efektywny),
            ),
            ("Data wystawienia", formatowanie.formatuj_date(oferta["data_wystawienia"]), None),
            ("Oferta ważna do", formatowanie.formatuj_date(oferta["data_waznosci"]), None),
            ("Waluta", waluta_tekst, None),
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
                wraplength=500,
                justify="left",
            ).pack(side="left")

        ctk.CTkFrame(naglowek, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        ctk.CTkLabel(
            self,
            text="Pozycje",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=1, column=0, sticky="w", padx=styl.ODSTEP_DUZY)

        tabela_pozycji = Tabela(self, kolumny=KOLUMNY_POZYCJI)
        tabela_pozycji.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_MALY, styl.ODSTEP_MALY),
        )
        formatery = {
            "cena_netto_grosze": lambda p: formatowanie.formatuj_kwote(
                p["cena_netto_grosze"], oferta["waluta"]
            ),
            "stawka_vat": lambda p: ETYKIETY_STAWEK_VAT.get(p["stawka_vat"], p["stawka_vat"]),
            "wartosc_netto_grosze": lambda p: formatowanie.formatuj_kwote(
                p["wartosc_netto_grosze"], oferta["waluta"]
            ),
            "wartosc_vat_grosze": lambda p: formatowanie.formatuj_kwote(
                p["wartosc_vat_grosze"], oferta["waluta"]
            ),
            "wartosc_brutto_grosze": lambda p: formatowanie.formatuj_kwote(
                p["wartosc_brutto_grosze"], oferta["waluta"]
            ),
        }
        tabela_pozycji.ustaw_dane(oferta["pozycje"], formatery=formatery)

        podsumowanie = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        podsumowanie.grid(
            row=3, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_SREDNI)
        )
        for etykieta, wartosc_grosze in [
            ("Razem netto", oferta["suma_netto_grosze"]),
            ("Razem VAT", oferta["suma_vat_grosze"]),
            ("Razem brutto", oferta["suma_brutto_grosze"]),
        ]:
            wiersz = ctk.CTkFrame(podsumowanie, fg_color="transparent")
            wiersz.pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_MALY, 0))
            ctk.CTkLabel(
                wiersz,
                text=etykieta,
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            ).pack(side="left")
            ctk.CTkLabel(
                wiersz,
                text=formatowanie.formatuj_kwote(wartosc_grosze, oferta["waluta"]),
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_TEKST_GLOWNY,
            ).pack(side="right")
        ctk.CTkFrame(podsumowanie, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        pasek_akcji = ctk.CTkFrame(self, fg_color="transparent")
        pasek_akcji.grid(
            row=4, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_MALY)
        )

        self._przycisk_pdf = ctk.CTkButton(
            pasek_akcji,
            text="Pobierz PDF",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._pobierz_pdf,
        )
        self._przycisk_pdf.pack(side="left", padx=(0, styl.ODSTEP_MALY))

        if oferta["status"] == "robocza":
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

        przejscia_mozliwe = PRZEJSCIA_DOZWOLONE_Z_GUI.get(oferta["status"], set())
        if "zaakceptowana" in przejscia_mozliwe:
            ctk.CTkButton(
                pasek_akcji,
                text="Oznacz jako zaakceptowana",
                font=styl.CZCIONKA_TRESC,
                fg_color="transparent",
                border_width=1,
                border_color=styl.KOLOR_OBRAMOWANIE,
                text_color=styl.KOLOR_SUKCES,
                hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                command=lambda: self._zmien_status("zaakceptowana"),
            ).pack(side="left", padx=(0, styl.ODSTEP_MALY))
        if "odrzucona" in przejscia_mozliwe:
            ctk.CTkButton(
                pasek_akcji,
                text="Oznacz jako odrzucona",
                font=styl.CZCIONKA_TRESC,
                fg_color="transparent",
                border_width=1,
                border_color=styl.KOLOR_OBRAMOWANIE,
                text_color=styl.KOLOR_BLAD,
                hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                command=lambda: self._zmien_status("odrzucona"),
            ).pack(side="left")

        if oferta["status"] == "zaakceptowana":
            pasek_faktury = ctk.CTkFrame(self, fg_color="transparent")
            pasek_faktury.grid(
                row=5, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
            )
            if oferta.get("faktura_wygenerowana_id"):
                ctk.CTkButton(
                    pasek_faktury,
                    text="Faktura już wystawiona",
                    font=styl.CZCIONKA_TRESC,
                    fg_color="transparent",
                    border_width=1,
                    border_color=styl.KOLOR_OBRAMOWANIE,
                    text_color=styl.KOLOR_TEKST_GLOWNY,
                    hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                    command=self._otworz_fakture_istniejaca,
                ).pack(side="left")
            else:
                self._przycisk_wystaw_fakture = ctk.CTkButton(
                    pasek_faktury,
                    text="Wystaw fakturę z tej oferty",
                    font=styl.CZCIONKA_TRESC,
                    fg_color="transparent",
                    border_width=1,
                    border_color=styl.KOLOR_OBRAMOWANIE,
                    text_color=styl.KOLOR_TEKST_GLOWNY,
                    hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                    command=self._wystaw_fakture,
                )
                self._przycisk_wystaw_fakture.pack(side="left")

    def _pobierz_pdf(self) -> None:
        ustaw_tekst_ladowania(self._przycisk_pdf, True, "Pobierz PDF", "Generowanie PDF...")

        def zadanie():
            return api_client.pobierz_pdf_oferty(self._oferta_id)

        def sukces(tresc: bytes) -> None:
            ustaw_tekst_ladowania(self._przycisk_pdf, False, "Pobierz PDF")
            numer_bezpieczny = self._oferta["numer"].replace("/", "_")
            sciezka = filedialog.asksaveasfilename(
                parent=self,
                title="Zapisz ofertę jako PDF",
                defaultextension=".pdf",
                initialfile=f"oferta_{numer_bezpieczny}.pdf",
                filetypes=[("Plik PDF", "*.pdf")],
            )
            if not sciezka:
                return
            try:
                with open(sciezka, "wb") as plik:
                    plik.write(tresc)
            except OSError as e:
                komunikat_bledu(self, f"Nie udało się zapisać pliku: {e}")
                return
            if messagebox.askyesno(
                "Zapisano", f"Zapisano plik:\n{sciezka}\n\nOtworzyć go teraz?", parent=self
            ):
                os.startfile(sciezka)

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_pdf, False, "Pobierz PDF")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zmien_status(self, nowy_status: str) -> None:
        etykieta = formatowanie.formatuj_status_oferty(nowy_status)
        if not messagebox.askyesno(
            "Potwierdzenie",
            f"Oznaczyć ofertę {self._oferta['numer']} jako „{etykieta}”?\n\n"
            "To rejestruje decyzję klienta podjętą poza aplikacją.",
            parent=self,
        ):
            return

        def zadanie():
            return api_client.zmien_status_oferty(self._oferta_id, nowy_status)

        def sukces(_wynik: dict) -> None:
            self._przeladuj()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _wystaw_fakture(self) -> None:
        ustaw_tekst_ladowania(
            self._przycisk_wystaw_fakture, True, "Wystaw fakturę z tej oferty", "Wystawianie..."
        )

        def zadanie():
            return api_client.wystaw_fakture_z_oferty(self._oferta_id)

        def sukces(faktura: dict) -> None:
            master = self.master
            self._on_zmiana()
            self.destroy()
            FormularzFaktury(master, on_zapisano=lambda: None, faktura=faktura)

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(
                self._przycisk_wystaw_fakture, False, "Wystaw fakturę z tej oferty"
            )
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _otworz_fakture_istniejaca(self) -> None:
        SzczegolyFaktury(self, faktura_id=self._oferta["faktura_wygenerowana_id"])

    def _przeladuj(self) -> None:
        oferta_id = self._oferta_id
        nazwa_klienta = self._nazwa_klienta
        on_zmiana = self._on_zmiana
        master = self.master
        on_zmiana()
        self.destroy()
        SzczegolyOferty(
            master, oferta_id=oferta_id, nazwa_klienta=nazwa_klienta, on_zmiana=on_zmiana
        )

    def _edytuj(self) -> None:
        FormularzOferty(self, on_zapisano=self._po_edycji, oferta=self._oferta)

    def _po_edycji(self) -> None:
        self._on_zmiana()
        self.destroy()
