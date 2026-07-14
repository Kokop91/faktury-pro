from typing import Callable

import customtkinter as ctk

from gui import api_client, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza


class FormularzInwentaryzacji(OknoFormularza):
    def __init__(self, master, on_zapisano: Callable[[], None]):
        super().__init__(master)
        self.title("Nowy spis inwentaryzacyjny")
        self.geometry("400x280")

        self._on_zapisano = on_zapisano
        self._id_wg_etykiety: dict[str, int] = {}

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        uruchom_w_tle(self, self._wczytaj_magazyny, self._po_wczytaniu, self._blad_wczytania)

    def _wczytaj_magazyny(self) -> list[dict]:
        return api_client.pobierz_magazyny(tylko_aktywne=True, limit=200)

    def _blad_wczytania(self, e: api_client.ApiError) -> None:
        komunikat_bledu(self, e.komunikat)
        self.destroy()

    def _po_wczytaniu(self, magazyny: list[dict]) -> None:
        self._etykieta_ladowania.destroy()
        self._zbuduj_formularz(magazyny)

    def _zbuduj_formularz(self, magazyny: list[dict]) -> None:
        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(
            fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        self._banner = Banner(kontener)

        etykieta_magazyn = ctk.CTkLabel(
            kontener,
            text="Magazyn *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        etykieta_magazyn.pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(
                fill="x", pady=(0, styl.ODSTEP_MALY), before=etykieta_magazyn
            )
        )

        etykiety = [m["nazwa"] for m in magazyny]
        self._id_wg_etykiety = {m["nazwa"]: m["id"] for m in magazyny}
        self._var_magazyn = ctk.StringVar(value=etykiety[0] if etykiety else "")
        ctk.CTkOptionMenu(
            kontener,
            values=etykiety or ["Brak magazynów"],
            variable=self._var_magazyn,
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkLabel(
            kontener,
            text=(
                "Spis automatycznie obejmie wszystkie towary magazynowe z ich "
                "aktualnym stanem systemowym w tym magazynie. Dopóki spis jest "
                "otwarty, nie da się otworzyć kolejnego dla tego samego magazynu."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=340,
            justify="left",
        ).pack(fill="x")

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
            text="Otwórz spis",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz,
        )
        self._przycisk_zapisz.pack(side="left", expand=True, fill="x")
        self.ustaw_akcje_zapisu(self._zapisz, self._przycisk_zapisz)

        self.zapamietaj_stan_poczatkowy()

    def _zapisz(self) -> None:
        magazyn_id = self._id_wg_etykiety.get(self._var_magazyn.get())
        if magazyn_id is None:
            self._banner.pokaz("Wybierz magazyn.")
            return
        self._banner.ukryj()

        ustaw_tekst_ladowania(self._przycisk_zapisz, True, "Otwórz spis", "Otwieranie...")

        def zadanie():
            return api_client.utworz_inwentaryzacje(magazyn_id)

        def sukces(wynik) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, f"Spis {wynik['numer']} otwarty.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zapisz, False, "Otwórz spis")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
