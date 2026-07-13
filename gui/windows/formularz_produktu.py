from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu

_ETYKIETY_STAWEK = [
    formatowanie.ETYKIETY_STAWEK_VAT[s] for s in formatowanie.KOLEJNOSC_STAWEK_VAT
]
_KLUCZE_WG_ETYKIETY_STAWKI = {
    formatowanie.ETYKIETY_STAWEK_VAT[s]: s for s in formatowanie.KOLEJNOSC_STAWEK_VAT
}


class FormularzProduktu(ctk.CTkToplevel):
    """Wylacznie tworzenie - backend (Faza 8) nie ma jeszcze PUT /produkty/{id}."""

    def __init__(self, master, on_zapisano: Callable[[], None]):
        super().__init__(master)
        self.title("Dodaj produkt")
        self.geometry("420x520")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()

        self._on_zapisano = on_zapisano

        kontener = ctk.CTkScrollableFrame(self, fg_color="transparent")
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
            text="Jednostka miary *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))
        self._pole_jednostka = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_jednostka.insert(0, "szt")
        self._pole_jednostka.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text="Cena netto *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))
        self._pole_cena = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_cena.insert(0, "0,00")
        self._pole_cena.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text="Domyślna stawka VAT",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))
        self._var_stawka = ctk.StringVar(value=_ETYKIETY_STAWEK[0])
        ctk.CTkOptionMenu(
            kontener,
            values=_ETYKIETY_STAWEK,
            variable=self._var_stawka,
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._var_towar = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            kontener,
            text="Towar magazynowy (ma stan; odznacz dla usługi)",
            font=styl.CZCIONKA_TRESC,
            variable=self._var_towar,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY), anchor="w")

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
            komunikat_bledu(self, "Nazwa produktu jest wymagana.")
            return None

        jednostka = self._pole_jednostka.get().strip()
        if not jednostka:
            komunikat_bledu(self, "Jednostka miary jest wymagana.")
            return None

        try:
            cena_grosze = formatowanie.parsuj_kwote(
                self._pole_cena.get(), wymagaj_dodatniej=False
            )
        except ValueError as e:
            komunikat_bledu(self, f"Nieprawidłowa cena netto: {e}")
            return None

        stawka = _KLUCZE_WG_ETYKIETY_STAWKI.get(self._var_stawka.get(), "23")

        return {
            "nazwa": nazwa,
            "jednostka_miary": jednostka,
            "cena_netto_grosze": cena_grosze,
            "domyslna_stawka_vat": stawka,
            "jest_magazynowy": bool(self._var_towar.get()),
        }

    def _zapisz(self) -> None:
        dane = self._zebrane_dane()
        if dane is None:
            return

        self._przycisk_zapisz.configure(state="disabled")

        def zadanie():
            return api_client.utworz_produkt(dane)

        def sukces(_wynik) -> None:
            self._on_zapisano()
            self.destroy()

        def blad(e: api_client.ApiError) -> None:
            self._przycisk_zapisz.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
