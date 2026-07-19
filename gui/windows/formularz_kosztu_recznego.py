from datetime import date
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza


class FormularzKosztuRecznego(OknoFormularza):
    """Recznie wprowadzony koszt spoza KSeF (Faza 25) - wydatki gotowkowe/
    niefakturowane, uzywane do wyliczenia marzy obok dokumentow kosztowych
    z KSeF (patrz app/services/rentownosc_service.py:marza_okresu)."""

    def __init__(
        self, master, on_zapisano: Callable[[], None], koszt: dict | None = None
    ):
        super().__init__(master)
        self._tryb_edycji = koszt is not None
        self._koszt_id = koszt["id"] if koszt else None
        self.title("Edytuj koszt" if self._tryb_edycji else "Dodaj koszt")
        self.geometry("420x460")

        self._on_zapisano = on_zapisano

        kontener = ctk.CTkScrollableFrame(self, fg_color="transparent")
        kontener.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)

        etykieta_data = ctk.CTkLabel(
            kontener, text="Data *", font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        etykieta_data.pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._banner = Banner(kontener)
        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(fill="x", pady=(0, styl.ODSTEP_MALY), before=etykieta_data)
        )
        self._pole_data = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_data.insert(
            0, formatowanie.formatuj_date(koszt["data"] if koszt else date.today())
        )
        self._pole_data.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener, text="Kwota *", font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_kwota = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_kwota.insert(
            0, formatowanie.grosze_do_wpisu(koszt["kwota_grosze"]) if koszt else "0,00"
        )
        self._pole_kwota.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener, text="Kategoria *", font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_kategoria = ctk.CTkEntry(
            kontener, font=styl.CZCIONKA_TRESC, placeholder_text="np. Paliwo, Materiały biurowe"
        )
        if koszt:
            self._pole_kategoria.insert(0, koszt["kategoria"])
        self._pole_kategoria.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener, text="Opis (opcjonalnie)", font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_opis = ctk.CTkTextbox(kontener, height=80, font=styl.CZCIONKA_TRESC)
        if koszt and koszt.get("opis"):
            self._pole_opis.insert("1.0", koszt["opis"])
        self._pole_opis.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        przyciski = ctk.CTkFrame(self, fg_color="transparent")
        przyciski.pack(fill="x", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY))

        ctk.CTkButton(
            przyciski, text="Anuluj", fg_color="transparent", border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE, text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY, command=self._zamknij_z_potwierdzeniem,
        ).pack(side="left", expand=True, fill="x", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_zapisz = ctk.CTkButton(
            przyciski, text="Zapisz", fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER, command=self._zapisz,
        )
        self._przycisk_zapisz.pack(side="left", expand=True, fill="x")
        self.ustaw_akcje_zapisu(self._zapisz, self._przycisk_zapisz)

        if self._tryb_edycji:
            ctk.CTkButton(
                self, text="Usuń koszt", fg_color="transparent",
                text_color=styl.KOLOR_BLAD, hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                command=self._usun,
            ).pack(fill="x", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY))

        self.zapamietaj_stan_poczatkowy()

    def _usun(self) -> None:
        if not messagebox.askyesno(
            "Potwierdzenie", "Usunąć ten koszt? Tej operacji nie można cofnąć.", parent=self
        ):
            return

        def zadanie():
            api_client.usun_koszt_reczny(self._koszt_id)

        def sukces(_wynik: None) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, "Koszt usunięty.")

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zebrane_dane(self) -> dict | None:
        try:
            data_kosztu = formatowanie.parsuj_date_pl(self._pole_data.get())
        except ValueError as e:
            self._banner.pokaz(f"Data: {e}")
            return None

        try:
            kwota_grosze = formatowanie.parsuj_kwote(self._pole_kwota.get())
        except ValueError as e:
            self._banner.pokaz(f"Nieprawidłowa kwota: {e}")
            return None

        kategoria = self._pole_kategoria.get().strip()
        if not kategoria:
            self._banner.pokaz("Kategoria jest wymagana.")
            return None

        opis = self._pole_opis.get("1.0", "end-1c").strip() or None

        self._banner.ukryj()
        return {
            "data": data_kosztu.isoformat(),
            "kwota_grosze": kwota_grosze,
            "kategoria": kategoria,
            "opis": opis,
        }

    def _zapisz(self) -> None:
        dane = self._zebrane_dane()
        if dane is None:
            return

        ustaw_tekst_ladowania(self._przycisk_zapisz, True, "Zapisz")

        def zadanie():
            if self._tryb_edycji:
                return api_client.aktualizuj_koszt_reczny(self._koszt_id, dane)
            return api_client.utworz_koszt_reczny(dane)

        def sukces(_wynik: dict) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, "Koszt zapisany.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zapisz, False, "Zapisz")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
