from typing import Any, Callable

import customtkinter as ctk

from gui import styl

TEKST_BRAK_DANYCH = "Brak danych do wyświetlenia."
TEKST_LADOWANIA = "Ładowanie..."


class Tabela(ctk.CTkScrollableFrame):
    """Reuzywalny komponent tabeli: jeden plaski grid (naglowek + wiersze danych),
    zeby kolumny naglowka i wierszy byly zawsze idealnie wyrownane. Klik w wiersz
    dziala tylko gdy podano on_wiersz_kliknij (np. tabela klientow jest nieklikalna).

    `sortowalne=True` (Faza 16C) wlacza klikalne naglowki kolumn - klikniecie
    sortuje po surowej wartosci `wiersz[klucz]`, chyba ze podano funkcje w
    `klucze_sortowania` (dla kolumn wyliczanych przez formater, np. nazwa
    klienta z klient_id). `on_zmiana_sortowania(klucz, malejaco)` pozwala
    wolajacemu zapisac ostatnie sortowanie (persystencja stanu widoku).
    """

    def __init__(
        self,
        master,
        kolumny: list[tuple[str, str, int]],
        on_wiersz_kliknij: Callable[[dict], None] | None = None,
        sortowalne: bool = False,
        sortowanie_poczatkowe: tuple[str, bool] | None = None,
        on_zmiana_sortowania: Callable[[str, bool], None] | None = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", styl.KOLOR_KARTA)
        super().__init__(master, **kwargs)
        self.kolumny = kolumny
        self.on_wiersz_kliknij = on_wiersz_kliknij
        self.sortowalne = sortowalne
        self.on_zmiana_sortowania = on_zmiana_sortowania
        self._sort_klucz, self._sort_malejaco = sortowanie_poczatkowe or (None, False)
        self._wiersze: list[list[ctk.CTkLabel]] = []
        self._placeholder: ctk.CTkLabel | None = None
        self._indeks_zaznaczony: int | None = None
        self._naglowki: dict[str, ctk.CTkLabel] = {}

        self._ostatnie_wiersze: list[dict] = []
        self._ostatnie_formatery: dict[str, Callable[[dict], str]] = {}
        self._ostatnie_kolory: dict[str, Callable[[dict], str]] = {}
        self._ostatnie_klucze_sortowania: dict[str, Callable[[dict], Any]] = {}

        for indeks, (_klucz, _etykieta, waga) in enumerate(kolumny):
            self.grid_columnconfigure(indeks, weight=waga)

        self._zbuduj_naglowek()

    def _zbuduj_naglowek(self) -> None:
        for indeks, (klucz, _etykieta, _waga) in enumerate(self.kolumny):
            label = ctk.CTkLabel(
                self,
                text="",
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                fg_color=styl.KOLOR_NAGLOWEK_TABELI,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
                padx=styl.ODSTEP_MALY,
                pady=styl.ODSTEP_MALY,
                cursor="hand2" if self.sortowalne else "",
            )
            label.grid(
                row=0,
                column=indeks,
                sticky="nsew",
                padx=styl.ODSTEP_RAMKA_TABELI,
                pady=(0, styl.ODSTEP_RAMKA_TABELI),
            )
            if self.sortowalne:
                label.bind("<Button-1>", lambda _z, k=klucz: self._kliknieto_naglowek(k))
            self._naglowki[klucz] = label
        self._odswiez_teksty_naglowka()

    def _odswiez_teksty_naglowka(self) -> None:
        for klucz, etykieta, _waga in self.kolumny:
            tekst = etykieta
            if self.sortowalne and klucz == self._sort_klucz:
                tekst += " ▼" if self._sort_malejaco else " ▲"
            self._naglowki[klucz].configure(text=tekst)

    def _kliknieto_naglowek(self, klucz: str) -> None:
        if self._sort_klucz == klucz:
            self._sort_malejaco = not self._sort_malejaco
        else:
            self._sort_klucz = klucz
            self._sort_malejaco = False
        if self.on_zmiana_sortowania:
            self.on_zmiana_sortowania(self._sort_klucz, self._sort_malejaco)
        self.ustaw_dane(
            self._ostatnie_wiersze, self._ostatnie_formatery, self._ostatnie_kolory,
            self._ostatnie_klucze_sortowania,
        )

    def _posortowane(self, wiersze: list[dict]) -> list[dict]:
        if not self.sortowalne or self._sort_klucz is None or not wiersze:
            return wiersze

        wyciagnij = self._ostatnie_klucze_sortowania.get(
            self._sort_klucz, lambda w: w.get(self._sort_klucz)
        )

        def klucz_sort(wiersz: dict):
            wartosc = wyciagnij(wiersz)
            return (wartosc is None, str(type(wartosc)), wartosc)

        try:
            return sorted(wiersze, key=klucz_sort, reverse=self._sort_malejaco)
        except TypeError:
            return sorted(
                wiersze,
                key=lambda w: str(wyciagnij(w) or "").lower(),
                reverse=self._sort_malejaco,
            )

    def pokaz_ladowanie(self) -> None:
        """Protokol WskaznikLadowania (gui/watki.py) - wywolywane automatycznie
        przez uruchom_w_tle tuz przed startem zadania w tle."""
        self._ustaw_placeholder(TEKST_LADOWANIA)

    def ukryj_ladowanie(self) -> None:
        """Druga polowa protokolu - w praktyce sciezka sukcesu od razu nadpisuje
        widok swiezymi danymi przez ustaw_dane(), wiec to ma znaczenie glownie
        przy bledzie (zeby napis 'Ladowanie...' nie zostal na stale)."""
        if self._placeholder is not None and not self._wiersze:
            self._ustaw_placeholder(TEKST_BRAK_DANYCH)

    def _ustaw_placeholder(self, tekst: str) -> None:
        for wiersz_etykiet in self._wiersze:
            for etykieta in wiersz_etykiet:
                etykieta.destroy()
        self._wiersze = []
        if self._placeholder is not None:
            self._placeholder.destroy()
        self._placeholder = ctk.CTkLabel(
            self,
            text=tekst,
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._placeholder.grid(
            row=1, column=0, columnspan=len(self.kolumny), pady=styl.ODSTEP_DUZY
        )
        self._indeks_zaznaczony = None

    def ustaw_dane(
        self,
        wiersze: list[dict],
        formatery: dict[str, Callable[[dict], str]] | None = None,
        kolory: dict[str, Callable[[dict], str]] | None = None,
        klucze_sortowania: dict[str, Callable[[dict], Any]] | None = None,
    ) -> None:
        formatery = formatery or {}
        kolory = kolory or {}
        self._ostatnie_wiersze = wiersze
        self._ostatnie_formatery = formatery
        self._ostatnie_kolory = kolory
        self._ostatnie_klucze_sortowania = klucze_sortowania or {}
        self._odswiez_teksty_naglowka()
        wiersze = self._posortowane(wiersze)

        for wiersz_etykiet in self._wiersze:
            for etykieta in wiersz_etykiet:
                etykieta.destroy()
        self._wiersze = []
        if self._placeholder is not None:
            self._placeholder.destroy()
            self._placeholder = None
        self._indeks_zaznaczony = None

        if not wiersze:
            self._ustaw_placeholder(TEKST_BRAK_DANYCH)
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
                kolor_formater = kolory.get(klucz)
                kolor_tekstu = (
                    kolor_formater(wiersz) if kolor_formater else styl.KOLOR_TEKST_GLOWNY
                )
                etykieta = ctk.CTkLabel(
                    self,
                    text=tekst,
                    font=styl.CZCIONKA_TRESC,
                    text_color=kolor_tekstu,
                    fg_color=kolor_tla,
                    anchor="w",
                    padx=styl.ODSTEP_MALY,
                    pady=styl.ODSTEP_MALY,
                )
                etykieta.grid(
                    row=indeks_wiersza + 1,
                    column=indeks_kolumny,
                    sticky="nsew",
                    padx=styl.ODSTEP_RAMKA_TABELI,
                    pady=styl.ODSTEP_RAMKA_TABELI,
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
