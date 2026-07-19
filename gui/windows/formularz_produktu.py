from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza

_ETYKIETY_STAWEK = [
    formatowanie.ETYKIETY_STAWEK_VAT[s] for s in formatowanie.KOLEJNOSC_STAWEK_VAT
]
_KLUCZE_WG_ETYKIETY_STAWKI = {
    formatowanie.ETYKIETY_STAWEK_VAT[s]: s for s in formatowanie.KOLEJNOSC_STAWEK_VAT
}


class FormularzProduktu(OknoFormularza):
    """Wylacznie tworzenie - backend (Faza 8) nie ma jeszcze PUT /produkty/{id}."""

    def __init__(self, master, on_zapisano: Callable[[], None]):
        super().__init__(master)
        self.title("Dodaj produkt")
        self.geometry("420x580")

        self._on_zapisano = on_zapisano

        kontener = ctk.CTkScrollableFrame(self, fg_color="transparent")
        kontener.pack(
            fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        etykieta_nazwa = ctk.CTkLabel(
            kontener,
            text="Nazwa *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        etykieta_nazwa.pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._banner = Banner(kontener)
        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(
                fill="x", pady=(0, styl.ODSTEP_MALY), before=etykieta_nazwa
            )
        )
        self._pole_nazwa = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_nazwa.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text="Jednostka miary *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_jednostka = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_jednostka.insert(0, "szt")
        self._pole_jednostka.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text="Cena netto *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_cena = ctk.CTkEntry(kontener, font=styl.CZCIONKA_TRESC)
        self._pole_cena.insert(0, "0,00")
        self._pole_cena.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        # Faza 25 - opcjonalny koszt zakupu/wytworzenia, do wskaznika
        # rentownosci per produkt (gui/windows/widok_rentownosci.py). Puste
        # pole = None (appka nie zna kosztu), NIGDY traktowane jako 0.
        ctk.CTkLabel(
            kontener,
            text="Koszt zakupu (opcjonalnie)",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        self._pole_koszt_zakupu = ctk.CTkEntry(
            kontener, font=styl.CZCIONKA_TRESC, placeholder_text="nieznany"
        )
        self._pole_koszt_zakupu.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            kontener,
            text="Domyślna stawka VAT",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
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

        # Faza 21 (split payment) - swiadomy wybor uzytkownika, appka nie moze
        # sama wiedziec, ze dany towar/usluga jest objety zalacznikiem nr 15.
        self._var_zalacznik_15 = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            kontener,
            text="Towar/usługa z załącznika nr 15 do ustawy o VAT",
            font=styl.CZCIONKA_TRESC,
            variable=self._var_zalacznik_15,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MIKRO), anchor="w")
        ctk.CTkLabel(
            kontener,
            text=(
                "Załącznik nr 15 to lista towarów i usług objętych obowiązkowym "
                "mechanizmem podzielonej płatności (m.in. wyroby stalowe, złom, "
                "elektronika, paliwa, części samochodowe, usługi budowlane) - "
                "zaznacz, jeśli ten produkt się na niej znajduje."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=380,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

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
        nazwa = self._pole_nazwa.get().strip()
        if not nazwa:
            self._banner.pokaz("Nazwa produktu jest wymagana.")
            return None

        jednostka = self._pole_jednostka.get().strip()
        if not jednostka:
            self._banner.pokaz("Jednostka miary jest wymagana.")
            return None

        try:
            cena_grosze = formatowanie.parsuj_kwote(
                self._pole_cena.get(), wymagaj_dodatniej=False
            )
        except ValueError as e:
            self._banner.pokaz(f"Nieprawidłowa cena netto: {e}")
            return None

        koszt_zakupu_tekst = self._pole_koszt_zakupu.get().strip()
        koszt_zakupu_grosze = None
        if koszt_zakupu_tekst:
            try:
                koszt_zakupu_grosze = formatowanie.parsuj_kwote(
                    koszt_zakupu_tekst, wymagaj_dodatniej=False
                )
            except ValueError as e:
                self._banner.pokaz(f"Nieprawidłowy koszt zakupu: {e}")
                return None

        stawka = _KLUCZE_WG_ETYKIETY_STAWKI.get(self._var_stawka.get(), "23")

        self._banner.ukryj()
        return {
            "nazwa": nazwa,
            "jednostka_miary": jednostka,
            "cena_netto_grosze": cena_grosze,
            "koszt_zakupu_grosze": koszt_zakupu_grosze,
            "domyslna_stawka_vat": stawka,
            "jest_magazynowy": bool(self._var_towar.get()),
            "objety_zalacznikiem_15": bool(self._var_zalacznik_15.get()),
        }

    def _zapisz(self) -> None:
        dane = self._zebrane_dane()
        if dane is None:
            return

        ustaw_tekst_ladowania(self._przycisk_zapisz, True, "Zapisz")

        def zadanie():
            return api_client.utworz_produkt(dane)

        def sukces(wynik) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, f"Produkt „{wynik['nazwa']}” zapisany.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zapisz, False, "Zapisz")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
