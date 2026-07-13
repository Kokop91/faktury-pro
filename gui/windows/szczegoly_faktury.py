import os
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_faktury import FormularzFaktury
from gui.windows.formularz_platnosci import FormularzPlatnosci
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

KOLUMNY_PLATNOSCI = [
    ("data_platnosci", "Data", 2),
    ("kwota_grosze", "Kwota", 2),
    ("notatka", "Notatka", 4),
]

ETYKIETY_STAWEK_VAT = {"23": "23%", "8": "8%", "5": "5%", "0": "0%", "zw": "zw."}

# Statusy faktury, dla ktorych rejestrowanie platnosci nie ma sensu biznesowego
# (mirror app/services/platnosci.py STATUSY_BLOKUJACE_PLATNOSC).
STATUSY_BLOKUJACE_PLATNOSC = frozenset({"robocza", "anulowana"})


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
        self.geometry("820x780")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()

        self._faktura_id = faktura_id
        self._faktura: dict | None = None
        self._platnosci: list[dict] = []
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
            platnosci = api_client.pobierz_platnosci_faktury(faktura_id)
            return faktura, nazwa_klienta, platnosci

        def sukces(wynik) -> None:
            faktura, nazwa_klienta, platnosci = wynik
            self._faktura = faktura
            self._nazwa_klienta = nazwa_klienta
            self._platnosci = platnosci
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

        status_efektywny = faktura.get("status_efektywny", faktura["status"])
        wiersze_info = [
            ("Klient", self._nazwa_klienta or f"#{faktura['klient_id']}", None),
            (
                "Status",
                formatowanie.formatuj_status(status_efektywny),
                formatowanie.kolor_statusu(status_efektywny),
            ),
            (
                "Data wystawienia",
                formatowanie.formatuj_date(faktura["data_wystawienia"]),
                None,
            ),
            (
                "Data sprzedaży",
                formatowanie.formatuj_date(faktura["data_sprzedazy"]),
                None,
            ),
            (
                "Termin płatności",
                formatowanie.formatuj_date(faktura["termin_platnosci"]),
                None,
            ),
            ("Waluta", waluta_tekst, None),
        ]
        if faktura.get("przyczyna_korekty"):
            wiersze_info.append(("Przyczyna korekty", faktura["przyczyna_korekty"], None))

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
        for etykieta, wartosc_grosze, kolor in [
            ("Razem netto", faktura["suma_netto_grosze"], None),
            ("Razem VAT", faktura["suma_vat_grosze"], None),
            ("Razem brutto", faktura["suma_brutto_grosze"], None),
            ("Zapłacono", faktura["suma_wplat_grosze"], styl.KOLOR_SUKCES),
            (
                "Pozostało do zapłaty",
                faktura["kwota_pozostala_grosze"],
                styl.KOLOR_BLAD if faktura["kwota_pozostala_grosze"] > 0 else styl.KOLOR_SUKCES,
            ),
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
                text_color=kolor or styl.KOLOR_TEKST_GLOWNY,
            ).pack(side="right")
        ctk.CTkFrame(podsumowanie, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        ctk.CTkLabel(
            self,
            text="Płatności",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=4, column=0, sticky="w", padx=styl.ODSTEP_DUZY)

        tabela_platnosci = Tabela(self, kolumny=KOLUMNY_PLATNOSCI, height=130)
        tabela_platnosci.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_MALY, styl.ODSTEP_MALY),
        )
        formatery_platnosci = {
            "data_platnosci": lambda p: formatowanie.formatuj_date(p["data_platnosci"]),
            "kwota_grosze": lambda p: formatowanie.formatuj_kwote(
                p["kwota_grosze"], faktura["waluta"]
            ),
            "notatka": lambda p: p.get("notatka") or "",
        }
        tabela_platnosci.ustaw_dane(self._platnosci, formatery=formatery_platnosci)

        pasek_akcji = ctk.CTkFrame(self, fg_color="transparent")
        pasek_akcji.grid(
            row=6, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
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

        if (
            faktura["status"] not in STATUSY_BLOKUJACE_PLATNOSC
            and faktura["kwota_pozostala_grosze"] > 0
        ):
            ctk.CTkButton(
                pasek_akcji,
                text="Dodaj płatność",
                font=styl.CZCIONKA_TRESC,
                fg_color="transparent",
                border_width=1,
                border_color=styl.KOLOR_OBRAMOWANIE,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                command=self._dodaj_platnosc,
            ).pack(side="left", padx=(styl.ODSTEP_MALY, 0))

    def _dodaj_platnosc(self) -> None:
        FormularzPlatnosci(
            self,
            faktura_id=self._faktura_id,
            kwota_pozostala_grosze=self._faktura["kwota_pozostala_grosze"],
            waluta=self._faktura["waluta"],
            on_zapisano=self._po_dodaniu_platnosci,
        )

    def _po_dodaniu_platnosci(self) -> None:
        # Okno szczegolow jest budowane raz w _zbuduj_widok (bez sciezki do
        # przebudowy w miejscu) - zamiast usuwac i ponownie dodawac widgety,
        # po prostu odswiezamy liste u rodzica i otwieramy nowe okno szczegolow
        # z aktualnymi danymi w miejsce tego.
        faktura_id = self._faktura_id
        nazwa_klienta = self._nazwa_klienta
        on_zmiana = self._on_zmiana
        master = self.master
        on_zmiana()
        self.destroy()
        SzczegolyFaktury(
            master,
            faktura_id=faktura_id,
            nazwa_klienta=nazwa_klienta,
            on_zmiana=on_zmiana,
        )

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
