from typing import Callable

import customtkinter as ctk

from gui import api_client, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza


class FormularzMagazynu(OknoFormularza):
    """Wylacznie tworzenie - backend (Faza 8) nie ma jeszcze PUT /magazyny/{id}."""

    def __init__(self, master, on_zapisano: Callable[[], None]):
        super().__init__(master)
        self.title("Dodaj magazyn")
        self.geometry("400x300")

        self._on_zapisano = on_zapisano

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(
            fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        etykieta_nazwa = ctk.CTkLabel(
            kontener,
            text="Nazwa *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        etykieta_nazwa.pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._banner = Banner(kontener)
        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(
                fill="x", pady=(0, styl.ODSTEP_MALY), before=etykieta_nazwa
            )
        )
        self._pole_nazwa = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_nazwa.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text="Lokalizacja",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_lokalizacja = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_lokalizacja.pack(fill="x")

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

        self.zapamietaj_stan_poczatkowy()

    def _zebrane_dane(self) -> dict | None:
        nazwa = self._pole_nazwa.get().strip()
        if not nazwa:
            self._banner.pokaz("Nazwa magazynu jest wymagana.")
            return None

        dane: dict = {"nazwa": nazwa}
        lokalizacja = self._pole_lokalizacja.get().strip()
        if lokalizacja:
            dane["lokalizacja"] = lokalizacja
        self._banner.ukryj()
        return dane

    def _zapisz(self) -> None:
        dane = self._zebrane_dane()
        if dane is None:
            return

        ustaw_tekst_ladowania(self._przycisk_zapisz, True, "Zapisz")

        def zadanie():
            return api_client.utworz_magazyn(dane)

        def sukces(wynik) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, f"Magazyn „{wynik['nazwa']}” zapisany.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zapisz, False, "Zapisz")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
