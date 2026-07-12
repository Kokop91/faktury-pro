from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from gui import api_client, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu

# (klucz, etykieta, wartosc_domyslna)
POLA = [
    ("nazwa", "Nazwa *", ""),
    ("nip", "NIP", ""),
    ("ulica", "Ulica", ""),
    ("kod_pocztowy", "Kod pocztowy", ""),
    ("miejscowosc", "Miejscowość", ""),
    ("kraj", "Kraj", "Polska"),
    ("email", "Email", ""),
    ("telefon", "Telefon", ""),
    ("domyslna_waluta", "Domyślna waluta", "PLN"),
    ("domyslny_termin_platnosci_dni", "Termin płatności (dni)", "14"),
]


class FormularzKlienta(ctk.CTkToplevel):
    def __init__(self, master, on_zapisano: Callable[[], None], klient: dict | None = None):
        super().__init__(master)
        self._tryb_edycji = klient is not None
        self._klient = klient
        self.title("Edytuj klienta" if self._tryb_edycji else "Dodaj klienta")
        self.geometry("420x660" if self._tryb_edycji else "420x600")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()

        self._on_zapisano = on_zapisano
        self._pola: dict[str, ctk.CTkEntry] = {}

        kontener = ctk.CTkScrollableFrame(self, fg_color="transparent")
        kontener.pack(
            fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        for klucz, etykieta, wartosc_domyslna in POLA:
            ctk.CTkLabel(
                kontener,
                text=etykieta,
                font=styl.CZCIONKA_ETYKIETA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                anchor="w",
            ).pack(fill="x", pady=(styl.ODSTEP_MALY, 2))
            wpis = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
            wartosc_startowa = wartosc_domyslna
            if self._tryb_edycji:
                wartosc_z_klienta = klient.get(klucz)
                wartosc_startowa = (
                    str(wartosc_z_klienta) if wartosc_z_klienta not in (None, "") else ""
                )
            if wartosc_startowa:
                wpis.insert(0, wartosc_startowa)
            wpis.pack(fill="x")
            self._pola[klucz] = wpis

        przyciski = ctk.CTkFrame(self, fg_color="transparent")
        przyciski.pack(fill="x", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_MALY))

        ctk.CTkButton(
            przyciski,
            text="Anuluj",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_zapisz = ctk.CTkButton(
            przyciski,
            text="Zapisz",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz,
        )
        self._przycisk_zapisz.pack(side="left", expand=True, fill="x")

        if self._tryb_edycji:
            self._przycisk_dezaktywuj = ctk.CTkButton(
                self,
                text="Dezaktywuj klienta",
                fg_color="transparent",
                border_width=1,
                border_color=styl.KOLOR_BLAD,
                text_color=styl.KOLOR_BLAD,
                hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                command=self._dezaktywuj,
            )
            self._przycisk_dezaktywuj.pack(
                fill="x", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
            )

    def _zebrane_dane(self) -> dict | None:
        nazwa = self._pola["nazwa"].get().strip()
        if not nazwa:
            komunikat_bledu(self, "Nazwa klienta jest wymagana.")
            return None

        dane: dict = {"nazwa": nazwa}
        for klucz in (
            "nip",
            "ulica",
            "kod_pocztowy",
            "miejscowosc",
            "kraj",
            "email",
            "telefon",
            "domyslna_waluta",
        ):
            wartosc = self._pola[klucz].get().strip()
            if wartosc:
                dane[klucz] = wartosc

        termin_tekst = self._pola["domyslny_termin_platnosci_dni"].get().strip()
        if termin_tekst:
            try:
                dane["domyslny_termin_platnosci_dni"] = int(termin_tekst)
            except ValueError:
                komunikat_bledu(self, "Termin płatności musi być liczbą całkowitą dni.")
                return None

        return dane

    def _zapisz(self) -> None:
        dane = self._zebrane_dane()
        if dane is None:
            return

        self._ustaw_przyciski_aktywne(False)

        def zadanie():
            if self._tryb_edycji:
                return api_client.aktualizuj_klienta(self._klient["id"], dane)
            return api_client.utworz_klienta(dane)

        def sukces(_wynik) -> None:
            self._on_zapisano()
            self.destroy()

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _dezaktywuj(self) -> None:
        if not messagebox.askyesno(
            "Dezaktywować klienta?",
            f"Czy na pewno dezaktywować klienta „{self._klient['nazwa']}”?\n\n"
            "Klient zniknie z domyślnej listy, ale jego dane i historia faktur "
            "pozostaną nietknięte. Będzie można go później przywrócić.",
            parent=self,
        ):
            return

        self._ustaw_przyciski_aktywne(False)

        def zadanie():
            api_client.usun_klienta(self._klient["id"])

        def sukces(_wynik) -> None:
            self._on_zapisano()
            self.destroy()

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _ustaw_przyciski_aktywne(self, aktywne: bool) -> None:
        stan = "normal" if aktywne else "disabled"
        self._przycisk_zapisz.configure(state=stan)
        if self._tryb_edycji:
            self._przycisk_dezaktywuj.configure(state=stan)
