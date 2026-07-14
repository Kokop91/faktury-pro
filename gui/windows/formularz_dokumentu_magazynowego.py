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

TYPY_KOLEJNOSC = formatowanie.KOLEJNOSC_TYPOW_DOKUMENTU_MAGAZYNOWEGO
_ETYKIETY_TYPOW = [
    formatowanie.ETYKIETY_TYPU_DOKUMENTU_MAGAZYNOWEGO[t] for t in TYPY_KOLEJNOSC
]
_KLUCZE_WG_ETYKIETY_TYPU = {
    formatowanie.ETYKIETY_TYPU_DOKUMENTU_MAGAZYNOWEGO[t]: t for t in TYPY_KOLEJNOSC
}


class _WierszPozycjiMagazynowej(ctk.CTkFrame):
    def __init__(
        self,
        master,
        etykiety_produktow: list[str],
        id_wg_etykiety: dict[str, int],
        on_usun: Callable[["_WierszPozycjiMagazynowej"], None],
    ):
        super().__init__(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self._on_usun = on_usun
        self._id_wg_etykiety = id_wg_etykiety

        for kolumna, waga in enumerate([3, 1, 0]):
            self.grid_columnconfigure(kolumna, weight=waga)

        self._var_produkt = ctk.StringVar(
            value=etykiety_produktow[0] if etykiety_produktow else ""
        )
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
        self.pole_ilosc.grid(row=0, column=1, sticky="ew", padx=styl.ODSTEP_MIKRO, pady=styl.ODSTEP_MALY)

        ctk.CTkButton(
            self,
            text="✕",
            width=28,
            fg_color="transparent",
            text_color=styl.KOLOR_BLAD,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=lambda: self._on_usun(self),
        ).grid(row=0, column=2, padx=(styl.ODSTEP_MIKRO, styl.ODSTEP_MALY))

    def pobierz_dane(self) -> dict:
        produkt_id = self._id_wg_etykiety.get(self._var_produkt.get())
        if produkt_id is None:
            raise ValueError("wybierz produkt")
        ilosc = formatowanie.parsuj_ilosc(self.pole_ilosc.get())
        return {"produkt_id": produkt_id, "ilosc": str(ilosc)}


class FormularzDokumentuMagazynowego(OknoFormularza):
    def __init__(self, master, on_zapisano: Callable[[], None]):
        super().__init__(master)
        self.title("Nowy dokument magazynowy")
        self.geometry("700x760")

        self._on_zapisano = on_zapisano
        self._magazyny: list[dict] = []
        self._produkty_magazynowe: list[dict] = []
        self._faktury: list[dict] = []
        self._id_faktury_wg_numeru: dict[str, int] = {}
        self._wiersze_pozycji: list[_WierszPozycjiMagazynowej] = []

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        uruchom_w_tle(self, self._wczytaj_dane_wstepne, self._po_wczytaniu, self._blad_wczytania)

    # -- ladowanie danych poczatkowych --------------------------------------------------

    def _wczytaj_dane_wstepne(self):
        magazyny = api_client.pobierz_magazyny(tylko_aktywne=True, limit=200)
        produkty = api_client.pobierz_produkty(tylko_aktywne=True, limit=200)
        faktury = api_client.pobierz_faktury(limit=200)
        return magazyny, produkty, faktury

    def _blad_wczytania(self, e: api_client.ApiError) -> None:
        komunikat_bledu(self, e.komunikat)
        self.destroy()

    def _po_wczytaniu(self, wynik) -> None:
        magazyny, produkty, faktury = wynik
        self._magazyny = magazyny
        # Tylko towary magazynowe - uslugi nigdy nie wystepuja w dokumentach
        # magazynowych (CLAUDE.md, regula 5).
        self._produkty_magazynowe = [p for p in produkty if p["jest_magazynowy"]]
        self._faktury = faktury
        self._id_faktury_wg_numeru = {f["numer"]: f["id"] for f in faktury}
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

        self._banner = Banner(self)
        self._banner.ustaw_geometrie(
            lambda: self._banner.grid(
                row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0)
            )
        )

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(row=1, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0))
        przewijany.grid_columnconfigure(0, weight=1)

        self._var_typ = ctk.StringVar(value=_ETYKIETY_TYPOW[0])
        self._pole(
            przewijany,
            0,
            "Typ dokumentu *",
            lambda m: ctk.CTkOptionMenu(
                m,
                values=_ETYKIETY_TYPOW,
                variable=self._var_typ,
                command=self._na_zmiane_typu,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ),
        )

        _ramka, self._pole_data = self._pole(
            przewijany, 1, "Data dokumentu * (DD.MM.RRRR)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_data.insert(0, formatowanie.formatuj_date(date.today()))

        etykiety_magazynow = [m["nazwa"] for m in self._magazyny]
        self._id_magazynu_wg_etykiety = {m["nazwa"]: m["id"] for m in self._magazyny}

        self._var_zrodlowy = ctk.StringVar(
            value=etykiety_magazynow[0] if etykiety_magazynow else ""
        )
        self._ramka_zrodlowy, _ = self._pole(
            przewijany,
            2,
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

        self._var_docelowy = ctk.StringVar(
            value=etykiety_magazynow[0] if etykiety_magazynow else ""
        )
        self._ramka_docelowy, _ = self._pole(
            przewijany,
            3,
            "Magazyn docelowy *",
            lambda m: ctk.CTkOptionMenu(
                m,
                values=etykiety_magazynow or ["Brak magazynów"],
                variable=self._var_docelowy,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ),
        )

        _ramka, self._pole_faktura = self._pole(
            przewijany,
            4,
            "Numer powiązanej faktury (opcjonalnie, informacyjnie)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC, placeholder_text="np. FV/2026/0001"),
        )

        # Pozycje
        ramka_pozycji = ctk.CTkFrame(przewijany, fg_color="transparent")
        ramka_pozycji.grid(
            row=5, column=0, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
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
            text="Zapisz dokument",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz,
        )
        self._przycisk_zapisz.grid(row=0, column=1, sticky="ew")
        self.ustaw_akcje_zapisu(self._zapisz, self._przycisk_zapisz)

        self._dodaj_wiersz_pozycji()
        self._na_zmiane_typu(self._var_typ.get())
        self.zapamietaj_stan_poczatkowy()

    # -- reakcje na zmiany --------------------------------------------------

    def _na_zmiane_typu(self, etykieta: str) -> None:
        typ = _KLUCZE_WG_ETYKIETY_TYPU.get(etykieta, "pz")
        wymaga_zrodlowy, wymaga_docelowy = formatowanie.WYMAGANE_MAGAZYNY_DOKUMENTU.get(
            typ, (False, False)
        )
        if wymaga_zrodlowy:
            self._ramka_zrodlowy.grid()
        else:
            self._ramka_zrodlowy.grid_remove()
        if wymaga_docelowy:
            self._ramka_docelowy.grid()
        else:
            self._ramka_docelowy.grid_remove()

    # -- pozycje --------------------------------------------------

    def _dodaj_wiersz_pozycji(self) -> None:
        etykiety_produktow = [
            f"{p['nazwa']} ({p['jednostka_miary']})" for p in self._produkty_magazynowe
        ]
        id_wg_etykiety = {
            f"{p['nazwa']} ({p['jednostka_miary']})": p["id"]
            for p in self._produkty_magazynowe
        }
        wiersz = _WierszPozycjiMagazynowej(
            self._kontener_wierszy,
            etykiety_produktow=etykiety_produktow,
            id_wg_etykiety=id_wg_etykiety,
            on_usun=self._usun_wiersz_pozycji,
        )
        wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        self._wiersze_pozycji.append(wiersz)

    def _usun_wiersz_pozycji(self, wiersz: _WierszPozycjiMagazynowej) -> None:
        wiersz.destroy()
        self._wiersze_pozycji.remove(wiersz)

    # -- zapis --------------------------------------------------

    def _zbierz_i_zwaliduj(self) -> dict | None:
        bledy: list[str] = []

        typ = _KLUCZE_WG_ETYKIETY_TYPU.get(self._var_typ.get(), "pz")
        wymaga_zrodlowy, wymaga_docelowy = formatowanie.WYMAGANE_MAGAZYNY_DOKUMENTU.get(
            typ, (False, False)
        )

        try:
            data_dokumentu = formatowanie.parsuj_date_pl(self._pole_data.get())
        except ValueError as e:
            data_dokumentu = None
            bledy.append(f"Data dokumentu: {e}")

        magazyn_zrodlowy_id = None
        if wymaga_zrodlowy:
            magazyn_zrodlowy_id = self._id_magazynu_wg_etykiety.get(self._var_zrodlowy.get())
            if magazyn_zrodlowy_id is None:
                bledy.append("Wybierz magazyn źródłowy.")

        magazyn_docelowy_id = None
        if wymaga_docelowy:
            magazyn_docelowy_id = self._id_magazynu_wg_etykiety.get(self._var_docelowy.get())
            if magazyn_docelowy_id is None:
                bledy.append("Wybierz magazyn docelowy.")

        if (
            wymaga_zrodlowy
            and wymaga_docelowy
            and magazyn_zrodlowy_id is not None
            and magazyn_zrodlowy_id == magazyn_docelowy_id
        ):
            bledy.append("Magazyn źródłowy i docelowy muszą być różne.")

        faktura_powiazana_id = None
        numer_faktury = self._pole_faktura.get().strip()
        if numer_faktury:
            faktura_powiazana_id = self._id_faktury_wg_numeru.get(numer_faktury)
            if faktura_powiazana_id is None:
                bledy.append(
                    f"Nie znaleziono faktury o numerze „{numer_faktury}” - "
                    "sprawdź numer albo zostaw pole puste."
                )

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

        dane: dict = {
            "typ": typ,
            "data_dokumentu": data_dokumentu.isoformat(),
            "pozycje": pozycje_dane,
        }
        if magazyn_zrodlowy_id is not None:
            dane["magazyn_zrodlowy_id"] = magazyn_zrodlowy_id
        if magazyn_docelowy_id is not None:
            dane["magazyn_docelowy_id"] = magazyn_docelowy_id
        if faktura_powiazana_id is not None:
            dane["faktura_powiazana_id"] = faktura_powiazana_id
        return dane

    def _zapisz(self) -> None:
        dane = self._zbierz_i_zwaliduj()
        if dane is None:
            return

        ustaw_tekst_ladowania(self._przycisk_zapisz, True, "Zapisz dokument")

        def zadanie():
            return api_client.utworz_dokument_magazynowy(dane)

        def sukces(wynik: dict) -> None:
            master = self.master
            ostrzezenia = wynik.get("ostrzezenia") or []
            self._on_zapisano()
            self.destroy()
            if ostrzezenia:
                komunikat_ostrzezenie(
                    master, "Dokument zapisany, ale:\n\n" + "\n\n".join(ostrzezenia)
                )
            else:
                pokaz_toast(master, f"Dokument {wynik['numer']} zapisany.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zapisz, False, "Zapisz dokument")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
