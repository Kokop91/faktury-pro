from typing import Callable

import customtkinter as ctk

from gui import api_client, styl
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
    def __init__(self, master, on_zapisano: Callable[[], None]):
        super().__init__(master)
        self.title("Dodaj klienta")
        self.geometry("420x600")
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
            if wartosc_domyslna:
                wpis.insert(0, wartosc_domyslna)
            wpis.pack(fill="x")
            self._pola[klucz] = wpis

        przyciski = ctk.CTkFrame(self, fg_color="transparent")
        przyciski.pack(fill="x", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY))

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
        ctk.CTkButton(
            przyciski,
            text="Zapisz",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz,
        ).pack(side="left", expand=True, fill="x")

    def _zapisz(self) -> None:
        nazwa = self._pola["nazwa"].get().strip()
        if not nazwa:
            komunikat_bledu(self, "Nazwa klienta jest wymagana.")
            return

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
                return

        try:
            api_client.utworz_klienta(dane)
        except api_client.ApiError as e:
            komunikat_bledu(self, e.komunikat)
            return

        self._on_zapisano()
        self.destroy()
