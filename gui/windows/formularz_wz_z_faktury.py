"""Wygenerowanie dokumentu WZ z istniejacej faktury (Faza 19) - swiadoma,
jednorazowa wygoda dla uzytkownika, NIE automatyczna regula w tle. Faktury i
magazyn pozostaja rozlacznymi modulami (Model B, CLAUDE.md) - ten formularz
tylko WSTEPNIE wypelnia zwykly formularz WZ danymi z faktury, uzytkownik wciaz
swiadomie przegladada/koryguje i zatwierdza, zanim cokolwiek zostanie zapisane.

PozycjaFaktury nie ma FK do Produkt (wolny tekst z Fazy 1), wiec dopasowanie
"ktora pozycja faktury to towar magazynowy" odbywa sie PO NAZWIE (dokladne
dopasowanie tekstu, bez rozroznienia wielkosci liter) wzgledem aktywnych,
magazynowych produktow z katalogu - ustalone z uzytkownikiem jako wystarczajace
na te faze, bo formularz i tak otwiera sie do wgladu/edycji przed zapisem.
"""

from datetime import date
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, ikony, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import (
    Banner,
    komunikat_bledu,
    komunikat_ostrzezenie,
    pokaz_toast,
    ustaw_tekst_ladowania,
)
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.wiersz_pozycji_magazynowej import WierszPozycjiMagazynowej


def dopasuj_pozycje_do_produktow(
    pozycje_faktury: list[dict], produkty_magazynowe: list[dict]
) -> tuple[list[tuple[dict, dict]], list[str]]:
    """Zwraca (dopasowane, pominiete_nazwy) - dopasowane to lista par
    (pozycja_faktury, produkt), pominiete_nazwy to nazwy pozycji faktury bez
    odpowiednika w aktywnych towarach magazynowych (uslugi albo literowka/inna
    nazwa niz w katalogu)."""
    produkty_wg_nazwy = {p["nazwa"].strip().lower(): p for p in produkty_magazynowe}
    dopasowane: list[tuple[dict, dict]] = []
    pominiete_nazwy: list[str] = []
    for pozycja in pozycje_faktury:
        produkt = produkty_wg_nazwy.get(pozycja["nazwa"].strip().lower())
        if produkt is not None:
            dopasowane.append((pozycja, produkt))
        else:
            pominiete_nazwy.append(pozycja["nazwa"])
    return dopasowane, pominiete_nazwy


class FormularzWzZFaktury(OknoFormularza):
    def __init__(
        self,
        master,
        faktura: dict,
        produkty_magazynowe: list[dict],
        on_zapisano: Callable[[], None],
    ):
        super().__init__(master)
        self.title(f"Wygeneruj WZ z faktury {faktura['numer']}")
        self.geometry("700x760")

        self._faktura = faktura
        self._produkty_magazynowe = produkty_magazynowe
        self._on_zapisano = on_zapisano
        self._magazyny: list[dict] = []
        self._wiersze_pozycji: list[WierszPozycjiMagazynowej] = []

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        uruchom_w_tle(self, self._wczytaj_magazyny, self._po_wczytaniu, self._blad_wczytania)

    # -- ladowanie danych poczatkowych --------------------------------------------------

    def _wczytaj_magazyny(self):
        return api_client.pobierz_magazyny(tylko_aktywne=True, limit=200)

    def _blad_wczytania(self, e: api_client.ApiError) -> None:
        komunikat_bledu(self, e.komunikat)
        self.destroy()

    def _po_wczytaniu(self, magazyny: list[dict]) -> None:
        self._magazyny = magazyny
        self._etykieta_ladowania.destroy()
        self._zbuduj_formularz()

    # -- pomocnicze --------------------------------------------------

    def _pole(self, master, wiersz: int, etykieta_tekst: str, widget_fabryka):
        ramka = ctk.CTkFrame(master, fg_color="transparent")
        ramka.grid(
            row=wiersz, column=0, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
        )
        ctk.CTkLabel(
            ramka,
            text=etykieta_tekst,
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        widget = widget_fabryka(ramka)
        widget.pack(fill="x")
        return ramka, widget

    # -- budowa formularza --------------------------------------------------

    def _zbuduj_formularz(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        dopasowane, pominiete_nazwy = dopasuj_pozycje_do_produktow(
            self._faktura["pozycje"], self._produkty_magazynowe
        )

        self._banner = Banner(self)
        self._banner.ustaw_geometrie(
            lambda: self._banner.grid(
                row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0)
            )
        )

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(row=1, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0))
        przewijany.grid_columnconfigure(0, weight=1)

        wiersz = 0
        ramka_info = ctk.CTkFrame(przewijany, fg_color="transparent")
        ramka_info.grid(row=wiersz, column=0, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI))
        ctk.CTkLabel(
            ramka_info,
            text=f"Powiązana faktura: {self._faktura['numer']}",
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).pack(fill="x")
        wiersz += 1

        etykiety_magazynow = [m["nazwa"] for m in self._magazyny]
        self._id_magazynu_wg_etykiety = {m["nazwa"]: m["id"] for m in self._magazyny}

        self._var_zrodlowy = ctk.StringVar(
            value=etykiety_magazynow[0] if etykiety_magazynow else ""
        )
        self._pole(
            przewijany,
            wiersz,
            "Magazyn źródłowy *",
            lambda m: ctk.CTkOptionMenu(
                m,
                values=etykiety_magazynow or ["Brak magazynów"],
                variable=self._var_zrodlowy,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ),
        )
        wiersz += 1

        _ramka, self._pole_data = self._pole(
            przewijany, wiersz, "Data dokumentu * (DD.MM.RRRR)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_data.insert(0, formatowanie.formatuj_date(date.today()))
        wiersz += 1

        if pominiete_nazwy:
            ramka_pominiete = ctk.CTkFrame(
                przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
            )
            ramka_pominiete.grid(
                row=wiersz, column=0, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
            )
            ctk.CTkLabel(
                ramka_pominiete,
                text=(
                    "Pominięto pozycje bez odpowiednika w aktywnych towarach "
                    "magazynowych: " + ", ".join(pominiete_nazwy)
                ),
                font=styl.CZCIONKA_DROBNA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                wraplength=600,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY)
            wiersz += 1

        # Pozycje
        ramka_pozycji = ctk.CTkFrame(przewijany, fg_color="transparent")
        ramka_pozycji.grid(
            row=wiersz, column=0, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
        )
        ramka_pozycji.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            ramka_pozycji, text="Pozycje", font=styl.NAGLOWEK_2, text_color=styl.KOLOR_TEKST_GLOWNY
        ).grid(row=0, column=0, sticky="w", pady=(0, styl.ODSTEP_MALY))
        self._kontener_wierszy = ctk.CTkFrame(ramka_pozycji, fg_color="transparent")
        self._kontener_wierszy.grid(row=1, column=0, sticky="ew")
        ctk.CTkButton(
            ramka_pozycji,
            text="Dodaj pozycję",
            image=ikony.ikona_adaptacyjna("plus"),
            compound="left",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._dodaj_wiersz_pozycji,
        ).grid(row=2, column=0, sticky="w", pady=(styl.ODSTEP_MALY, 0))

        # Przyciski akcji
        pasek_przyciskow = ctk.CTkFrame(self, fg_color="transparent")
        pasek_przyciskow.grid(row=2, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)
        pasek_przyciskow.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            pasek_przyciskow,
            text="Anuluj",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._zamknij_z_potwierdzeniem,
        ).grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_zapisz = ctk.CTkButton(
            pasek_przyciskow,
            text="Zapisz WZ",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz,
        )
        self._przycisk_zapisz.grid(row=0, column=1, sticky="ew")
        self.ustaw_akcje_zapisu(self._zapisz, self._przycisk_zapisz)

        for pozycja, produkt in dopasowane:
            self._dodaj_wiersz_pozycji(
                produkt_wybrany=f"{produkt['nazwa']} ({produkt['jednostka_miary']})",
                ilosc_poczatkowa=str(pozycja["ilosc"]),
            )
        self.zapamietaj_stan_poczatkowy()

    # -- pozycje --------------------------------------------------

    def _dodaj_wiersz_pozycji(
        self, produkt_wybrany: str | None = None, ilosc_poczatkowa: str | None = None
    ) -> None:
        etykiety_produktow = [
            f"{p['nazwa']} ({p['jednostka_miary']})" for p in self._produkty_magazynowe
        ]
        id_wg_etykiety = {
            f"{p['nazwa']} ({p['jednostka_miary']})": p["id"]
            for p in self._produkty_magazynowe
        }
        wiersz = WierszPozycjiMagazynowej(
            self._kontener_wierszy,
            etykiety_produktow=etykiety_produktow,
            id_wg_etykiety=id_wg_etykiety,
            on_usun=self._usun_wiersz_pozycji,
            produkt_wybrany=produkt_wybrany,
            ilosc_poczatkowa=ilosc_poczatkowa,
        )
        wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        self._wiersze_pozycji.append(wiersz)

    def _usun_wiersz_pozycji(self, wiersz: WierszPozycjiMagazynowej) -> None:
        wiersz.destroy()
        self._wiersze_pozycji.remove(wiersz)

    # -- zapis --------------------------------------------------

    def _zbierz_i_zwaliduj(self) -> dict | None:
        bledy: list[str] = []

        try:
            data_dokumentu = formatowanie.parsuj_date_pl(self._pole_data.get())
        except ValueError as e:
            data_dokumentu = None
            bledy.append(f"Data dokumentu: {e}")

        magazyn_zrodlowy_id = self._id_magazynu_wg_etykiety.get(self._var_zrodlowy.get())
        if magazyn_zrodlowy_id is None:
            bledy.append("Wybierz magazyn źródłowy.")

        if not self._wiersze_pozycji:
            bledy.append("Dodaj co najmniej jedną pozycję.")
        pozycje_dane: list[dict] = []
        for indeks, wiersz in enumerate(self._wiersze_pozycji, start=1):
            try:
                pozycje_dane.append(wiersz.pobierz_dane())
            except ValueError as e:
                bledy.append(f"Pozycja {indeks}: {e}")

        if bledy:
            self._banner.pokaz("\n".join(bledy))
            return None
        self._banner.ukryj()

        return {
            "typ": "wz",
            "data_dokumentu": data_dokumentu.isoformat(),
            "magazyn_zrodlowy_id": magazyn_zrodlowy_id,
            "faktura_powiazana_id": self._faktura["id"],
            "pozycje": pozycje_dane,
        }

    def _zapisz(self) -> None:
        dane = self._zbierz_i_zwaliduj()
        if dane is None:
            return

        ustaw_tekst_ladowania(self._przycisk_zapisz, True, "Zapisz WZ")

        def zadanie():
            return api_client.utworz_dokument_magazynowy(dane)

        def sukces(wynik: dict) -> None:
            master = self.master
            ostrzezenia = wynik.get("ostrzezenia") or []
            numer = wynik["dokument"]["numer"]
            self._on_zapisano()
            self.destroy()
            if ostrzezenia:
                komunikat_ostrzezenie(
                    master,
                    f"Dokument {numer} zapisany, ale:\n\n" + "\n\n".join(ostrzezenia),
                )
            else:
                pokaz_toast(master, f"Dokument {numer} zapisany.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zapisz, False, "Zapisz WZ")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
