import os
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_faktury import FormularzFaktury
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


class SzczegolyFaktury(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        faktura_id: int,
        nazwa_klienta: str | None = None,
        on_zmiana: Callable[[], None] | None = None,
    ):
        super().__init__(master)
        self.title("Szczegóły faktury")
        self.geometry("820x660")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()

        self._faktura_id = faktura_id
        self._faktura: dict | None = None
        self._nazwa_klienta = nazwa_klienta
        self._on_zmiana = on_zmiana or (lambda: None)

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        self._zaladuj(faktura_id)

    def _zaladuj(self, faktura_id: int) -> None:
        def zadanie():
            faktura = api_client.pobierz_fakture(faktura_id)
            nazwa_klienta = self._nazwa_klienta
            if nazwa_klienta is None:
                klient = api_client.pobierz_klienta(faktura["klient_id"])
                nazwa_klienta = klient["nazwa"]
            return faktura, nazwa_klienta

        def sukces(wynik) -> None:
            faktura, nazwa_klienta = wynik
            self._faktura = faktura
            self._nazwa_klienta = nazwa_klienta
            self._etykieta_ladowania.destroy()
            self._zbuduj_widok(faktura)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            self.destroy()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_widok(self, faktura: dict) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        naglowek = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        naglowek.grid(
            row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        tytul_tekst = (
            f"{formatowanie.formatuj_typ_dokumentu(faktura['typ_dokumentu'])} "
            f"— {faktura['numer']}"
        )
        ctk.CTkLabel(
            naglowek,
            text=tytul_tekst,
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(anchor="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        waluta_tekst = faktura["waluta"]
        if faktura["waluta"] != "PLN":
            waluta_tekst += f" (kurs {faktura['kurs_waluty']})"

        wiersze_info = [
            ("Klient", self._nazwa_klienta or f"#{faktura['klient_id']}"),
            ("Status", formatowanie.formatuj_status(faktura["status"])),
            ("Data wystawienia", formatowanie.formatuj_date(faktura["data_wystawienia"])),
            ("Data sprzedaży", formatowanie.formatuj_date(faktura["data_sprzedazy"])),
            ("Termin płatności", formatowanie.formatuj_date(faktura["termin_platnosci"])),
            ("Waluta", waluta_tekst),
        ]
        if faktura.get("przyczyna_korekty"):
            wiersze_info.append(("Przyczyna korekty", faktura["przyczyna_korekty"]))

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
                p["cena_netto_grosze"], faktura["waluta"]
            ),
            "stawka_vat": lambda p: ETYKIETY_STAWEK_VAT.get(
                p["stawka_vat"], p["stawka_vat"]
            ),
            "wartosc_netto_grosze": lambda p: formatowanie.formatuj_kwote(
                p["wartosc_netto_grosze"], faktura["waluta"]
            ),
            "wartosc_vat_grosze": lambda p: formatowanie.formatuj_kwote(
                p["wartosc_vat_grosze"], faktura["waluta"]
            ),
            "wartosc_brutto_grosze": lambda p: formatowanie.formatuj_kwote(
                p["wartosc_brutto_grosze"], faktura["waluta"]
            ),
        }
        tabela_pozycji.ustaw_dane(faktura["pozycje"], formatery=formatery)

        podsumowanie = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        podsumowanie.grid(
            row=3, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_SREDNI)
        )
        for etykieta, wartosc_grosze in [
            ("Razem netto", faktura["suma_netto_grosze"]),
            ("Razem VAT", faktura["suma_vat_grosze"]),
            ("Razem brutto", faktura["suma_brutto_grosze"]),
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
                text=formatowanie.formatuj_kwote(wartosc_grosze, faktura["waluta"]),
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_TEKST_GLOWNY,
            ).pack(side="right")
        ctk.CTkFrame(podsumowanie, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        pasek_akcji = ctk.CTkFrame(self, fg_color="transparent")
        pasek_akcji.grid(
            row=4, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
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

        if faktura["status"] == "robocza":
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
            ).pack(side="left")

    def _pobierz_pdf(self) -> None:
        self._przycisk_pdf.configure(state="disabled")

        def zadanie():
            return api_client.pobierz_pdf_faktury(self._faktura_id)

        def sukces(tresc: bytes) -> None:
            self._przycisk_pdf.configure(state="normal")
            numer_bezpieczny = self._faktura["numer"].replace("/", "_")
            sciezka = filedialog.asksaveasfilename(
                parent=self,
                title="Zapisz fakturę jako PDF",
                defaultextension=".pdf",
                initialfile=f"faktura_{numer_bezpieczny}.pdf",
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
            self._przycisk_pdf.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _edytuj(self) -> None:
        FormularzFaktury(self, on_zapisano=self._po_edycji, faktura=self._faktura)

    def _po_edycji(self) -> None:
        self._on_zmiana()
        self.destroy()
