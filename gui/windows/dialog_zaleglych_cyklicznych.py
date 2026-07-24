from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoDialogu


class DialogZaleglychCyklicznych(OknoDialogu):
    """Okno startowe (Faza 15, KLUCZOWE wymaganie) - appka jest desktopowa i
    nie dziala 24/7, wiec zamiast systemowego harmonogramu sprawdzamy zaleglosci
    RAZ, przy kazdym uruchomieniu (patrz glowne_okno.py). Nigdy nie generuje nic
    automatycznie - to zawsze swiadoma decyzja uzytkownika (Wygeneruj wybrane/
    wszystkie), z opcja "Później" (proste zamkniecie, bez potwierdzenia -
    odlozenie decyzji nie jest "utrata danych")."""

    def __init__(self, master, zalegle: list[dict], on_wygenerowano: Callable[[], None]):
        super().__init__(master)
        self.title("Faktury cykliczne do wygenerowania")
        self.geometry("620x560")

        self._zalegle = zalegle
        self._on_wygenerowano = on_wygenerowano
        self._zaznaczenia: list[ctk.BooleanVar] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text=f"Do wygenerowania: {len(zalegle)} faktur cyklicznych",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI))

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(row=1, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY)
        przewijany.grid_columnconfigure(0, weight=1)

        for indeks, pozycja in enumerate(zalegle):
            zaznaczona = ctk.BooleanVar(value=True)
            self._zaznaczenia.append(zaznaczona)

            wiersz = ctk.CTkFrame(
                przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
            )
            wiersz.grid(row=indeks, column=0, sticky="ew", pady=(0, styl.ODSTEP_MALY))
            wiersz.grid_columnconfigure(1, weight=1)

            ctk.CTkCheckBox(
                wiersz,
                text="",
                variable=zaznaczona,
                width=20,
                fg_color=styl.KOLOR_AKCENT,
                hover_color=styl.KOLOR_AKCENT_HOVER,
            ).grid(row=0, column=0, padx=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY), pady=styl.ODSTEP_MALY)

            tekst_opisu = (
                f"{pozycja['klient_nazwa']} — "
                f"{formatowanie.formatuj_typ_dokumentu(pozycja['typ_dokumentu'])} "
                f"za {formatowanie.formatuj_date(pozycja['okres'])}"
            )
            ctk.CTkLabel(
                wiersz, text=tekst_opisu, font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
            ).grid(row=0, column=1, sticky="w")

            ctk.CTkLabel(
                wiersz,
                text=formatowanie.formatuj_kwote(
                    pozycja["kwota_brutto_szacowana_grosze"], pozycja["waluta"]
                ),
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_TEKST_GLOWNY,
            ).grid(row=0, column=2, padx=styl.ODSTEP_SREDNI)

        pasek_przyciskow = ctk.CTkFrame(self, fg_color="transparent")
        pasek_przyciskow.grid(row=2, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)
        pasek_przyciskow.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            pasek_przyciskow,
            text="Później",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_wybrane = ctk.CTkButton(
            pasek_przyciskow,
            text="Wygeneruj wybrane",
            fg_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            hover_color=styl.KOLOR_TEKST_GLOWNY,
            command=self._wygeneruj_wybrane,
        )
        self._przycisk_wybrane.grid(row=0, column=1, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_wszystkie = ctk.CTkButton(
            pasek_przyciskow,
            text="Wygeneruj wszystkie",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._wygeneruj_wszystkie,
        )
        self._przycisk_wszystkie.grid(row=0, column=2, sticky="ew")

    def _ustaw_przyciski_aktywne(self, aktywne: bool) -> None:
        stan = "normal" if aktywne else "disabled"
        self._przycisk_wybrane.configure(state=stan)
        self._przycisk_wszystkie.configure(state=stan)

    def _wygeneruj_wybrane(self) -> None:
        wybrane = [
            {"szablon_id": pozycja["szablon_id"], "okres": pozycja["okres"]}
            for pozycja, zaznaczona in zip(self._zalegle, self._zaznaczenia)
            if zaznaczona.get()
        ]
        if not wybrane:
            komunikat_bledu(self, "Zaznacz co najmniej jedną fakturę do wygenerowania.")
            return
        self._generuj(wybrane, "Wygeneruj wybrane")

    def _wygeneruj_wszystkie(self) -> None:
        wszystkie = [
            {"szablon_id": pozycja["szablon_id"], "okres": pozycja["okres"]}
            for pozycja in self._zalegle
        ]
        self._generuj(wszystkie, "Wygeneruj wszystkie")

    def _generuj(self, pozycje: list[dict], tekst_przycisku: str) -> None:
        self._ustaw_przyciski_aktywne(False)
        ustaw_tekst_ladowania(self._przycisk_wszystkie, True, "Wygeneruj wszystkie", "Generowanie...")

        def zadanie():
            return api_client.generuj_faktury_cykliczne(pozycje)

        def sukces(wygenerowane: list[dict]) -> None:
            master = self.master
            liczba = len(wygenerowane)
            self._on_wygenerowano()
            self.destroy()
            pokaz_toast(
                master,
                f"Wygenerowano {liczba} faktur cyklicznych (jako robocze - przejrzyj przed wystawieniem).",
            )

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            ustaw_tekst_ladowania(self._przycisk_wszystkie, False, "Wygeneruj wszystkie")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
