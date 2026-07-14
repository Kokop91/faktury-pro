from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from gui import api_client, styl
from gui.integracje_gui import pobierz_z_gus, sprawdz_biala_liste
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza

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


class FormularzKlienta(OknoFormularza):
    def __init__(self, master, on_zapisano: Callable[[], None], klient: dict | None = None):
        super().__init__(master)
        self._tryb_edycji = klient is not None
        self._klient = klient
        self.title("Edytuj klienta" if self._tryb_edycji else "Dodaj klienta")
        self.geometry("420x660" if self._tryb_edycji else "420x600")

        self._on_zapisano = on_zapisano
        self._pola: dict[str, ctk.CTkEntry] = {}

        kontener = ctk.CTkScrollableFrame(self, fg_color="transparent")
        kontener.pack(
            fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        self._banner = Banner(kontener)
        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(
                fill="x", pady=(0, styl.ODSTEP_MALY), before=self._pierwsza_etykieta
            )
        )
        self._pierwsza_etykieta = None

        for klucz, etykieta, wartosc_domyslna in POLA:
            etykieta_pola = ctk.CTkLabel(
                kontener,
                text=etykieta,
                font=styl.CZCIONKA_ETYKIETA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                anchor="w",
            )
            etykieta_pola.pack(fill="x", pady=(styl.ODSTEP_MALY, 2))
            if self._pierwsza_etykieta is None:
                self._pierwsza_etykieta = etykieta_pola

            wartosc_startowa = wartosc_domyslna
            if self._tryb_edycji:
                wartosc_z_klienta = klient.get(klucz)
                wartosc_startowa = (
                    str(wartosc_z_klienta) if wartosc_z_klienta not in (None, "") else ""
                )

            if klucz == "nip":
                # NIP dostaje wlasny wiersz z przyciskami integracji (Faza 14) -
                # pobranie danych z GUS wypelnia reszte pol, sprawdzenie w
                # bialej liscie dziala na tym, co akurat jest wpisane w pole.
                wiersz_nip = ctk.CTkFrame(kontener, fg_color="transparent")
                wiersz_nip.pack(fill="x")
                wiersz_nip.grid_columnconfigure(0, weight=1)
                wpis = ctk.CTkEntry(wiersz_nip, font=styl.CZCIONKA_TRESC)
                wpis.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
                self._przycisk_gus = ctk.CTkButton(
                    wiersz_nip,
                    text="Pobierz z GUS",
                    font=styl.CZCIONKA_DROBNA,
                    width=110,
                    fg_color="transparent",
                    border_width=1,
                    border_color=styl.KOLOR_OBRAMOWANIE,
                    text_color=styl.KOLOR_TEKST_GLOWNY,
                    hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                    command=self._pobierz_z_gus,
                )
                self._przycisk_gus.grid(row=0, column=1)

                self._etykieta_biala_lista = ctk.CTkLabel(
                    kontener,
                    text="",
                    font=styl.CZCIONKA_DROBNA,
                    anchor="w",
                    wraplength=360,
                    justify="left",
                )
                self._etykieta_biala_lista.pack(fill="x", pady=(styl.ODSTEP_MIKRO, 0))
                self._przycisk_biala_lista = ctk.CTkButton(
                    kontener,
                    text="Sprawdź w białej liście",
                    font=styl.CZCIONKA_DROBNA,
                    fg_color="transparent",
                    border_width=1,
                    border_color=styl.KOLOR_OBRAMOWANIE,
                    text_color=styl.KOLOR_TEKST_GLOWNY,
                    hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                    command=self._sprawdz_biala_liste,
                )
                self._przycisk_biala_lista.pack(anchor="w", pady=(styl.ODSTEP_MIKRO, 0))
            else:
                wpis = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
                wpis.pack(fill="x")

            if wartosc_startowa:
                wpis.insert(0, wartosc_startowa)
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
            command=self._zamknij_z_potwierdzeniem,
        ).pack(side="left", expand=True, fill="x", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_zapisz = ctk.CTkButton(
            przyciski,
            text="Zapisz",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz,
        )
        self._przycisk_zapisz.pack(side="left", expand=True, fill="x")
        self.ustaw_akcje_zapisu(self._zapisz, self._przycisk_zapisz)

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

        self.zapamietaj_stan_poczatkowy()

    def _pobierz_z_gus(self) -> None:
        def wypelnij(podmiot: dict) -> None:
            mapowanie = {
                "nazwa": "nazwa",
                "ulica": "ulica",
                "kod_pocztowy": "kod_pocztowy",
                "miejscowosc": "miejscowosc",
            }
            for klucz_podmiotu, klucz_pola in mapowanie.items():
                wartosc = podmiot.get(klucz_podmiotu)
                if wartosc:
                    self._pola[klucz_pola].delete(0, "end")
                    self._pola[klucz_pola].insert(0, wartosc)

        pobierz_z_gus(
            self, self._pola["nip"].get(), self._przycisk_gus, self._banner, wypelnij
        )

    def _sprawdz_biala_liste(self) -> None:
        sprawdz_biala_liste(
            self,
            self._pola["nip"].get(),
            self._przycisk_biala_lista,
            self._etykieta_biala_lista,
            klient_id=self._klient["id"] if self._tryb_edycji else None,
        )

    def _zebrane_dane(self) -> dict | None:
        nazwa = self._pola["nazwa"].get().strip()
        if not nazwa:
            self._banner.pokaz("Nazwa klienta jest wymagana.")
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
                self._banner.pokaz("Termin płatności musi być liczbą całkowitą dni.")
                return None

        self._banner.ukryj()
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

        def sukces(wynik) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, f"Klient „{wynik['nazwa']}” zapisany.")

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
            nazwa_klienta = self._klient["nazwa"]
            self.destroy()
            pokaz_toast(self.master, f"Klient „{nazwa_klienta}” dezaktywowany.")

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _ustaw_przyciski_aktywne(self, aktywne: bool) -> None:
        ustaw_tekst_ladowania(self._przycisk_zapisz, not aktywne, "Zapisz")
        if self._tryb_edycji:
            stan = "normal" if aktywne else "disabled"
            self._przycisk_dezaktywuj.configure(state=stan)
