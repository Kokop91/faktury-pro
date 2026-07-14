from typing import Callable

import customtkinter as ctk

from gui import formatowanie, styl

_ETYKIETY_STAWEK = [
    formatowanie.ETYKIETY_STAWEK_VAT[s] for s in formatowanie.KOLEJNOSC_STAWEK_VAT
]
_KLUCZE_WG_ETYKIETY_STAWKI = {
    formatowanie.ETYKIETY_STAWEK_VAT[s]: s for s in formatowanie.KOLEJNOSC_STAWEK_VAT
}


class WierszPozycji(ctk.CTkFrame):
    """Wiersz pozycji (nazwa/ilosc/jednostka/cena/stawka VAT + podglad wartosci) -
    wspoldzielony przez formularz faktury i formularz szablonu cyklicznego
    (Faza 15), bo ksztalt pozycji jest identyczny w obu miejscach."""

    def __init__(
        self,
        master,
        on_usun: Callable[["WierszPozycji"], None],
        on_zmiana: Callable[[], None],
    ):
        super().__init__(master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA)
        self._on_usun = on_usun
        self._on_zmiana = on_zmiana

        for kolumna, waga in enumerate([3, 1, 1, 1, 1, 1, 0]):
            self.grid_columnconfigure(kolumna, weight=waga)

        self.pole_nazwa = ctk.CTkEntry(self, placeholder_text="Nazwa", font=styl.CZCIONKA_TRESC)
        self.pole_nazwa.grid(row=0, column=0, sticky="ew", padx=(styl.ODSTEP_MALY, styl.ODSTEP_MIKRO), pady=styl.ODSTEP_MALY)

        self.pole_ilosc = ctk.CTkEntry(self, placeholder_text="Ilość", font=styl.CZCIONKA_TRESC)
        self.pole_ilosc.insert(0, "1")
        self.pole_ilosc.grid(row=0, column=1, sticky="ew", padx=styl.ODSTEP_MIKRO, pady=styl.ODSTEP_MALY)

        self.pole_jednostka = ctk.CTkEntry(self, placeholder_text="J.m.", font=styl.CZCIONKA_TRESC)
        self.pole_jednostka.insert(0, "szt.")
        self.pole_jednostka.grid(row=0, column=2, sticky="ew", padx=styl.ODSTEP_MIKRO, pady=styl.ODSTEP_MALY)

        self.pole_cena = ctk.CTkEntry(self, placeholder_text="Cena netto", font=styl.CZCIONKA_TRESC)
        self.pole_cena.grid(row=0, column=3, sticky="ew", padx=styl.ODSTEP_MIKRO, pady=styl.ODSTEP_MALY)

        self.stawka_var = ctk.StringVar(value=_ETYKIETY_STAWEK[0])
        self.menu_stawka = ctk.CTkOptionMenu(
            self,
            values=_ETYKIETY_STAWEK,
            variable=self.stawka_var,
            command=lambda _wartosc: self._wywolaj_zmiane(),
            width=70,
        )
        self.menu_stawka.grid(row=0, column=4, sticky="ew", padx=styl.ODSTEP_MIKRO, pady=styl.ODSTEP_MALY)

        self.etykieta_wartosc = ctk.CTkLabel(
            self, text="—", font=styl.CZCIONKA_TRESC, text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="e"
        )
        self.etykieta_wartosc.grid(row=0, column=5, sticky="ew", padx=styl.ODSTEP_MIKRO)

        ctk.CTkButton(
            self,
            text="✕",
            width=28,
            fg_color="transparent",
            text_color=styl.KOLOR_BLAD,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=lambda: self._on_usun(self),
        ).grid(row=0, column=6, padx=(styl.ODSTEP_MIKRO, styl.ODSTEP_MALY))

        for pole in (self.pole_nazwa, self.pole_ilosc, self.pole_jednostka, self.pole_cena):
            pole.bind("<KeyRelease>", lambda _zdarzenie: self._wywolaj_zmiane())

        self._odswiez_podglad()

    def _wywolaj_zmiane(self) -> None:
        self._odswiez_podglad()
        self._on_zmiana()

    def _odswiez_podglad(self) -> None:
        _netto, _vat, brutto = self.podsumowanie_grosze()
        self.etykieta_wartosc.configure(
            text=formatowanie.grosze_do_wpisu(brutto) if brutto else "—"
        )

    def podsumowanie_grosze(self) -> tuple[int, int, int]:
        """Best-effort podglad (netto, vat, brutto) - (0, 0, 0) gdy wiersz niekompletny."""
        try:
            cena_grosze = formatowanie.parsuj_kwote(self.pole_cena.get())
            ilosc = formatowanie.parsuj_ilosc(self.pole_ilosc.get())
            stawka = _KLUCZE_WG_ETYKIETY_STAWKI.get(self.stawka_var.get(), "23")
            return formatowanie.oblicz_podglad_pozycji(cena_grosze, ilosc, stawka)
        except ValueError:
            return 0, 0, 0

    def ustaw_ograniczenie_zw(self, wlaczone: bool) -> None:
        if wlaczone:
            etykieta_zw = formatowanie.ETYKIETY_STAWEK_VAT["zw"]
            self.stawka_var.set(etykieta_zw)
            self.menu_stawka.configure(values=[etykieta_zw], state="disabled")
        else:
            self.menu_stawka.configure(values=_ETYKIETY_STAWEK, state="normal")
        self._odswiez_podglad()

    def pobierz_dane(self) -> dict:
        nazwa = self.pole_nazwa.get().strip()
        if not nazwa:
            raise ValueError("nazwa jest wymagana")
        ilosc = formatowanie.parsuj_ilosc(self.pole_ilosc.get())
        jednostka = self.pole_jednostka.get().strip()
        if not jednostka:
            raise ValueError("jednostka miary jest wymagana")
        cena_grosze = formatowanie.parsuj_kwote(self.pole_cena.get())
        stawka = _KLUCZE_WG_ETYKIETY_STAWKI.get(self.stawka_var.get())
        if stawka is None:
            raise ValueError("wybierz stawkę VAT")
        return {
            "nazwa": nazwa,
            "ilosc": str(ilosc),
            "jednostka_miary": jednostka,
            "cena_netto_grosze": cena_grosze,
            "stawka_vat": stawka,
        }

    def wczytaj_dane(self, pozycja: dict) -> None:
        self.pole_nazwa.delete(0, "end")
        self.pole_nazwa.insert(0, pozycja["nazwa"])
        self.pole_ilosc.delete(0, "end")
        self.pole_ilosc.insert(0, str(pozycja["ilosc"]).replace(".", ","))
        self.pole_jednostka.delete(0, "end")
        self.pole_jednostka.insert(0, pozycja["jednostka_miary"])
        self.pole_cena.delete(0, "end")
        self.pole_cena.insert(0, formatowanie.grosze_do_wpisu(pozycja["cena_netto_grosze"]))
        etykieta = formatowanie.ETYKIETY_STAWEK_VAT.get(pozycja["stawka_vat"])
        if etykieta:
            self.stawka_var.set(etykieta)
        self._odswiez_podglad()
