"""Dialogi wykonania i przywracania kopii zapasowej (Faza 22, Etap 4).

Haslo szyfrowania NIGDY nie jest zapamietywane (patrz gui/kopia_zapasowa.py) -
oba dialogi zawsze proszaja o nie na nowo. Przywracanie jest operacja
NIEODWRACALNA (nadpisuje CALA biezaca baze danych), wiec ma dwa niezalezne
potwierdzenia: jawny komunikat ostrzegawczy PRZED wpisaniem hasla, i wymuszone
zamkniecie calej aplikacji PO powodzeniu (stan appki w pamieci jest niespojny
z nowa zawartoscia bazy - bezpieczniej zaczac od czystego startu niz probowac
"na zywo" odswiezyc kazde otwarte okno)."""
import os
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from gui import kopia_zapasowa as kz
from gui import styl
from gui.api_client import ApiError
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza

DLUGOSC_MIN_HASLA = 8


class DialogWykonajBackup(OknoFormularza):
    def __init__(self, master, katalog_docelowy: str, on_wykonano: Callable[[], None]):
        super().__init__(master)
        self.title("Wykonaj kopię zapasową")
        self.geometry("440x380")
        self.resizable(False, False)

        self._katalog_docelowy = katalog_docelowy
        self._on_wykonano = on_wykonano

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)

        self._banner = Banner(kontener)
        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        )

        ctk.CTkLabel(
            kontener,
            text=(
                f"Kopia zostanie zapisana w:\n{katalog_docelowy}\n\n"
                "Ustaw hasło szyfrowania kopii - INNE niż hasło logowania do "
                "aplikacji. Zapamiętaj je lub zapisz w bezpiecznym miejscu: "
                "appka NIGDZIE go nie zapisuje, więc bez niego przywrócenie "
                "tej kopii nie będzie możliwe."
            ),
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            wraplength=380,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkLabel(
            kontener, text="Hasło szyfrowania *", font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_haslo = ctk.CTkEntry(kontener, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_haslo.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener, text="Powtórz hasło *", font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_haslo2 = ctk.CTkEntry(kontener, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_haslo2.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk = ctk.CTkButton(
            kontener, text="Wykonaj kopię zapasową", fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER, command=self._wykonaj,
        )
        self._przycisk.pack(fill="x")
        self.ustaw_akcje_zapisu(self._wykonaj, self._przycisk)
        self.zapamietaj_stan_poczatkowy()

    def _wykonaj(self) -> None:
        haslo = self._pole_haslo.get()
        haslo2 = self._pole_haslo2.get()
        if len(haslo) < DLUGOSC_MIN_HASLA:
            self._banner.pokaz(f"Hasło szyfrowania musi mieć co najmniej {DLUGOSC_MIN_HASLA} znaków.")
            return
        if haslo != haslo2:
            self._banner.pokaz("Hasła nie są identyczne.")
            return
        self._banner.ukryj()

        ustaw_tekst_ladowania(
            self._przycisk, True, "Wykonaj kopię zapasową", "Wykonywanie kopii zapasowej..."
        )

        def zadanie():
            try:
                return kz.wykonaj_backup(Path(self._katalog_docelowy), haslo)
            except kz.BladKopiiZapasowej as e:
                raise ApiError(str(e)) from e

        def sukces(plik: Path) -> None:
            master = self.master
            self._on_wykonano()
            self.destroy()
            messagebox.showinfo(
                "Kopia zapasowa wykonana",
                f"Kopia zapisana jako:\n{plik.name}\n\nw katalogu:\n{plik.parent}",
                parent=master,
            )

        def blad(e: ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk, False, "Wykonaj kopię zapasową")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)


class DialogPrzywrocBackup(OknoFormularza):
    def __init__(self, master):
        super().__init__(master)
        self.title("Przywróć z kopii zapasowej")
        self.geometry("460x420")
        self.resizable(False, False)

        self._plik: Path | None = None

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)

        self._banner = Banner(kontener)
        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        )

        ostrzezenie = ctk.CTkFrame(
            kontener, fg_color=styl.KOLOR_BLAD_TLO, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        ostrzezenie.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))
        ctk.CTkLabel(
            ostrzezenie,
            text=(
                "UWAGA: przywrócenie NADPISZE CAŁKOWICIE bieżące dane (wszystkie "
                "faktury, klientów, magazyn) danymi z wybranej kopii zapasowej. "
                "Tej operacji nie można cofnąć. Po zakończeniu aplikacja zostanie "
                "zamknięta - uruchom ją ponownie."
            ),
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_BLAD,
            wraplength=380,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_SREDNI)

        ctk.CTkLabel(
            kontener, text="Plik kopii zapasowej *", font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        wiersz_pliku = ctk.CTkFrame(kontener, fg_color="transparent")
        wiersz_pliku.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        wiersz_pliku.grid_columnconfigure(0, weight=1)
        self._etykieta_plik = ctk.CTkLabel(
            wiersz_pliku, text="Nie wybrano", font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_plik.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        ctk.CTkButton(
            wiersz_pliku, text="Wybierz...", font=styl.CZCIONKA_DROBNA, width=90,
            fg_color="transparent", border_width=1, border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY, hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._wybierz_plik,
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            kontener, text="Hasło szyfrowania kopii *", font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_haslo = ctk.CTkEntry(kontener, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_haslo.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk = ctk.CTkButton(
            kontener, text="Przywróć (nadpisze bieżące dane)", fg_color=styl.KOLOR_BLAD,
            hover_color=styl.KOLOR_BLAD, command=self._przywroc,
        )
        self._przycisk.pack(fill="x")
        self.zapamietaj_stan_poczatkowy()

    def _wybierz_plik(self) -> None:
        sciezka = filedialog.askopenfilename(
            parent=self,
            title="Wybierz plik kopii zapasowej",
            filetypes=[("Kopia zapasowa Faktury Pro", "*.fpbk"), ("Wszystkie pliki", "*.*")],
        )
        if not sciezka:
            return
        self._plik = Path(sciezka)
        self._etykieta_plik.configure(text=self._plik.name, text_color=styl.KOLOR_TEKST_GLOWNY)

    def _przywroc(self) -> None:
        if self._plik is None:
            self._banner.pokaz("Wybierz plik kopii zapasowej.")
            return
        haslo = self._pole_haslo.get()
        if not haslo:
            self._banner.pokaz("Podaj hasło szyfrowania kopii zapasowej.")
            return
        self._banner.ukryj()

        if not messagebox.askyesno(
            "Potwierdź przywrócenie danych",
            "Zamierzasz nadpisać WSZYSTKIE bieżące dane aplikacji zawartością "
            f"kopii zapasowej „{self._plik.name}”. Tej operacji nie można cofnąć.\n\n"
            "Czy na pewno chcesz kontynuować?",
            icon="warning",
            parent=self,
        ):
            return

        ustaw_tekst_ladowania(
            self._przycisk, True, "Przywróć (nadpisze bieżące dane)", "Przywracanie danych..."
        )

        def zadanie():
            try:
                kz.przywroc_z_backupu(self._plik, haslo)
            except kz.NieprawidloweHaslo as e:
                raise ApiError(str(e)) from e
            except kz.BladKopiiZapasowej as e:
                raise ApiError(str(e)) from e

        def sukces(_wynik) -> None:
            messagebox.showinfo(
                "Dane przywrócone",
                "Dane zostały przywrócone z kopii zapasowej.\n\n"
                "Aplikacja zostanie teraz zamknięta - uruchom ją ponownie, "
                "aby zobaczyć przywrócone dane.",
                parent=self,
            )
            from gui import proces_aplikacji

            proces_aplikacji.zatrzymaj_wszystko()
            os._exit(0)

        def blad(e: ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk, False, "Przywróć (nadpisze bieżące dane)")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
