from typing import Callable

import customtkinter as ctk

from gui import formatowanie, styl


class WierszPozycjiMagazynowej(ctk.CTkFrame):
    """Wiersz produkt+ilosc na formularzu dokumentu magazynowego - wydzielony z
    formularz_dokumentu_magazynowego.py (Faza 8), bo Faza 19 (WZ z faktury) tez
    go potrzebuje, ten sam wzorzec co gui/windows/wiersz_pozycji.py dla pozycji
    faktur (tez uzywany przez dwa rozne formularze)."""

    def __init__(
        self,
        master,
        etykiety_produktow: list[str],
        id_wg_etykiety: dict[str, int],
        on_usun: Callable[["WierszPozycjiMagazynowej"], None],
        produkt_wybrany: str | None = None,
        ilosc_poczatkowa: str | None = None,
        pokaz_cene_zakupu: bool = False,
        cena_zakupu_poczatkowa_grosze: int | None = None,
    ):
        super().__init__(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self._on_usun = on_usun
        self._id_wg_etykiety = id_wg_etykiety
        self._pokaz_cene_zakupu = pokaz_cene_zakupu

        # Kolumna ceny zakupu (Faza 27) - opcjonalna, tylko dla PZ (patrz
        # komentarz przy PozycjaDokumentuMagazynowego.cena_zakupu_netto_grosze) -
        # dlatego jest wlaczana/wylaczana calym parametrem konstruktora, nie
        # ukrywana warunkowo po fakcie.
        wagi_kolumn = [3, 1, 1, 0] if pokaz_cene_zakupu else [3, 1, 0]
        for kolumna, waga in enumerate(wagi_kolumn):
            self.grid_columnconfigure(kolumna, weight=waga)

        wartosc_poczatkowa = (
            produkt_wybrany
            if produkt_wybrany in etykiety_produktow
            else (etykiety_produktow[0] if etykiety_produktow else "")
        )
        self._var_produkt = ctk.StringVar(value=wartosc_poczatkowa)
        ctk.CTkOptionMenu(
            self,
            values=etykiety_produktow or ["Brak towarów magazynowych"],
            variable=self._var_produkt,
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=0, column=0, sticky="ew", padx=(styl.ODSTEP_MALY, styl.ODSTEP_MIKRO), pady=styl.ODSTEP_MALY)

        self.pole_ilosc = ctk.CTkEntry(
            self, placeholder_text="Ilość", font=styl.CZCIONKA_TRESC
        )
        if ilosc_poczatkowa is not None:
            self.pole_ilosc.insert(0, ilosc_poczatkowa)
        self.pole_ilosc.grid(row=0, column=1, sticky="ew", padx=styl.ODSTEP_MIKRO, pady=styl.ODSTEP_MALY)

        self.pole_cena_zakupu: ctk.CTkEntry | None = None
        if pokaz_cene_zakupu:
            self.pole_cena_zakupu = ctk.CTkEntry(
                self, placeholder_text="Cena zakupu netto (opcj.)", font=styl.CZCIONKA_TRESC
            )
            if cena_zakupu_poczatkowa_grosze is not None:
                zlote, reszta_groszy = divmod(cena_zakupu_poczatkowa_grosze, 100)
                self.pole_cena_zakupu.insert(0, f"{zlote},{reszta_groszy:02d}")
            self.pole_cena_zakupu.grid(
                row=0, column=2, sticky="ew", padx=styl.ODSTEP_MIKRO, pady=styl.ODSTEP_MALY
            )

        ctk.CTkButton(
            self,
            text="✕",
            width=28,
            fg_color="transparent",
            text_color=styl.KOLOR_BLAD,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=lambda: self._on_usun(self),
        ).grid(row=0, column=(3 if pokaz_cene_zakupu else 2), padx=(styl.ODSTEP_MIKRO, styl.ODSTEP_MALY))

    def pobierz_dane(self) -> dict:
        produkt_id = self._id_wg_etykiety.get(self._var_produkt.get())
        if produkt_id is None:
            raise ValueError("wybierz produkt")
        ilosc = formatowanie.parsuj_ilosc(self.pole_ilosc.get())
        dane = {"produkt_id": produkt_id, "ilosc": str(ilosc)}
        if self.pole_cena_zakupu is not None:
            tekst_ceny = self.pole_cena_zakupu.get().strip()
            if tekst_ceny:
                dane["cena_zakupu_netto_grosze"] = formatowanie.parsuj_kwote(
                    tekst_ceny, wymagaj_dodatniej=False
                )
        return dane
