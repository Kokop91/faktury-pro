from typing import Callable

import customtkinter as ctk

from gui import api_client, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu


class FormularzMagazynu(ctk.CTkToplevel):
    """Wylacznie tworzenie - backend (Faza 8) nie ma jeszcze PUT /magazyny/{id}."""

    def __init__(self, master, on_zapisano: Callable[[], None]):
        super().__init__(master)
        self.title("Dodaj magazyn")
        self.geometry("400x300")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()

        self._on_zapisano = on_zapisano

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(
            fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        ctk.CTkLabel(
            kontener,
            text="Nazwa *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))
        self._pole_nazwa = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_nazwa.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text="Lokalizacja",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))
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

    def _zebrane_dane(self) -> dict | None:
        nazwa = self._pole_nazwa.get().strip()
        if not nazwa:
            komunikat_bledu(self, "Nazwa magazynu jest wymagana.")
            return None

        dane: dict = {"nazwa": nazwa}
        lokalizacja = self._pole_lokalizacja.get().strip()
        if lokalizacja:
            dane["lokalizacja"] = lokalizacja
        return dane

    def _zapisz(self) -> None:
        dane = self._zebrane_dane()
        if dane is None:
            return

        self._przycisk_zapisz.configure(state="disabled")

        def zadanie():
            return api_client.utworz_magazyn(dane)

        def sukces(_wynik) -> None:
            self._on_zapisano()
            self.destroy()

        def blad(e: api_client.ApiError) -> None:
            self._przycisk_zapisz.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
