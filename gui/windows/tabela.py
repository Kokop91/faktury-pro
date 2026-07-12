from typing import Callable

import customtkinter as ctk

from gui import styl


class Tabela(ctk.CTkScrollableFrame):
    """Reuzywalny komponent tabeli: jeden plaski grid (naglowek + wiersze danych),
    zeby kolumny naglowka i wierszy byly zawsze idealnie wyrownane. Klik w wiersz
    dziala tylko gdy podano on_wiersz_kliknij (np. tabela klientow jest nieklikalna).
    """

    def __init__(
        self,
        master,
        kolumny: list[tuple[str, str, int]],
        on_wiersz_kliknij: Callable[[dict], None] | None = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", styl.KOLOR_KARTA)
        super().__init__(master, **kwargs)
        self.kolumny = kolumny
        self.on_wiersz_kliknij = on_wiersz_kliknij
        self._wiersze: list[list[ctk.CTkLabel]] = []
        self._placeholder: ctk.CTkLabel | None = None
        self._indeks_zaznaczony: int | None = None

        for indeks, (_klucz, _etykieta, waga) in enumerate(kolumny):
            self.grid_columnconfigure(indeks, weight=waga)

        self._zbuduj_naglowek()

    def _zbuduj_naglowek(self) -> None:
        for indeks, (_klucz, etykieta, _waga) in enumerate(self.kolumny):
            label = ctk.CTkLabel(
                self,
                text=etykieta,
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                fg_color=styl.KOLOR_NAGLOWEK_TABELI,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
                padx=styl.ODSTEP_MALY,
                pady=styl.ODSTEP_MALY,
            )
            label.grid(row=0, column=indeks, sticky="nsew", padx=1, pady=(0, 1))

    def ustaw_dane(
        self,
        wiersze: list[dict],
        formatery: dict[str, Callable[[dict], str]] | None = None,
    ) -> None:
        formatery = formatery or {}

        for wiersz_etykiet in self._wiersze:
            for etykieta in wiersz_etykiet:
                etykieta.destroy()
        self._wiersze = []
        if self._placeholder is not None:
            self._placeholder.destroy()
            self._placeholder = None
        self._indeks_zaznaczony = None

        if not wiersze:
            self._placeholder = ctk.CTkLabel(
                self,
                text="Brak danych do wyświetlenia.",
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            )
            self._placeholder.grid(
                row=1, column=0, columnspan=len(self.kolumny), pady=styl.ODSTEP_DUZY
            )
            return

        for indeks_wiersza, wiersz in enumerate(wiersze):
            kolor_tla = self._kolor_wiersza(indeks_wiersza)
            etykiety_w_wierszu = []
            for indeks_kolumny, (klucz, _etykieta, _waga) in enumerate(self.kolumny):
                formater = formatery.get(klucz)
                if formater:
                    tekst = formater(wiersz)
                else:
                    wartosc = wiersz.get(klucz)
                    tekst = "" if wartosc is None else str(wartosc)
                etykieta = ctk.CTkLabel(
                    self,
                    text=tekst,
                    font=styl.CZCIONKA_TRESC,
                    text_color=styl.KOLOR_TEKST_GLOWNY,
                    fg_color=kolor_tla,
                    anchor="w",
                    padx=styl.ODSTEP_MALY,
                    pady=styl.ODSTEP_MALY,
                )
                etykieta.grid(
                    row=indeks_wiersza + 1,
                    column=indeks_kolumny,
                    sticky="nsew",
                    padx=1,
                    pady=1,
                )
                if self.on_wiersz_kliknij is not None:
                    etykieta.configure(cursor="hand2")
                    etykieta.bind(
                        "<Button-1>",
                        lambda _zdarzenie, w=wiersz, i=indeks_wiersza: (
                            self._kliknieto_wiersz(w, i)
                        ),
                    )
                etykiety_w_wierszu.append(etykieta)
            self._wiersze.append(etykiety_w_wierszu)

    def _kolor_wiersza(self, indeks_wiersza: int) -> str:
        return (
            styl.KOLOR_WIERSZ_PARZYSTY
            if indeks_wiersza % 2 == 0
            else styl.KOLOR_WIERSZ_NIEPARZYSTY
        )

    def _kliknieto_wiersz(self, wiersz: dict, indeks: int) -> None:
        self._podswietl_wiersz(indeks)
        self.on_wiersz_kliknij(wiersz)

    def _podswietl_wiersz(self, indeks: int) -> None:
        if self._indeks_zaznaczony is not None:
            poprzedni_kolor = self._kolor_wiersza(self._indeks_zaznaczony)
            for etykieta in self._wiersze[self._indeks_zaznaczony]:
                etykieta.configure(fg_color=poprzedni_kolor)

        for etykieta in self._wiersze[indeks]:
            etykieta.configure(fg_color=styl.KOLOR_WIERSZ_ZAZNACZONY)
        self._indeks_zaznaczony = indeks
