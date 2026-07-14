from datetime import date
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza


class FormularzPlatnosci(OknoFormularza):
    def __init__(
        self,
        master,
        faktura_id: int,
        kwota_pozostala_grosze: int,
        waluta: str,
        on_zapisano: Callable[[], None],
    ):
        super().__init__(master)
        self.title("Dodaj płatność")
        self.geometry("360x380")

        self._faktura_id = faktura_id
        self._on_zapisano = on_zapisano

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(
            fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        self._banner = Banner(kontener)

        etykieta_pozostalo = ctk.CTkLabel(
            kontener,
            text=(
                "Pozostało do zapłaty: "
                f"{formatowanie.formatuj_kwote(kwota_pozostala_grosze, waluta)}"
            ),
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        etykieta_pozostalo.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))
        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(
                fill="x", pady=(0, styl.ODSTEP_MALY), before=etykieta_pozostalo
            )
        )

        ctk.CTkLabel(
            kontener,
            text="Data płatności * (DD.MM.RRRR)",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_data = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_data.insert(0, formatowanie.formatuj_date(date.today()))
        self._pole_data.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text=f"Kwota ({waluta}) *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_kwota = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_kwota.insert(0, formatowanie.grosze_do_wpisu(kwota_pozostala_grosze))
        self._pole_kwota.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text="Notatka",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_notatka = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_notatka.pack(fill="x")

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
        try:
            data_platnosci = formatowanie.parsuj_date_pl(self._pole_data.get())
        except ValueError as e:
            self._banner.pokaz(f"Nieprawidłowa data płatności: {e}")
            return None

        try:
            kwota_grosze = formatowanie.parsuj_kwote(self._pole_kwota.get())
        except ValueError as e:
            self._banner.pokaz(f"Nieprawidłowa kwota: {e}")
            return None

        dane: dict = {
            "data_platnosci": data_platnosci.isoformat(),
            "kwota_grosze": kwota_grosze,
        }
        notatka = self._pole_notatka.get().strip()
        if notatka:
            dane["notatka"] = notatka
        self._banner.ukryj()
        return dane

    def _zapisz(self) -> None:
        dane = self._zebrane_dane()
        if dane is None:
            return

        ustaw_tekst_ladowania(self._przycisk_zapisz, True, "Zapisz")

        def zadanie():
            return api_client.dodaj_platnosc(self._faktura_id, dane)

        def sukces(_wynik) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, "Płatność zapisana.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zapisz, False, "Zapisz")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
