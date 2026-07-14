from datetime import date
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, ikony, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.wiersz_pozycji import WierszPozycji

TYPY_KOLEJNOSC = [
    t for t in formatowanie.ETYKIETY_TYPU_DOKUMENTU
    if t in formatowanie.DOZWOLONE_TYPY_SZABLONU_CYKLICZNEGO
]
_ETYKIETY_TYPOW = [formatowanie.ETYKIETY_TYPU_DOKUMENTU[t] for t in TYPY_KOLEJNOSC]
_KLUCZE_WG_ETYKIETY_TYPU = {
    formatowanie.ETYKIETY_TYPU_DOKUMENTU[t]: t for t in TYPY_KOLEJNOSC
}

_ETYKIETY_CZESTOTLIWOSCI = [
    formatowanie.ETYKIETY_CZESTOTLIWOSCI[c] for c in formatowanie.KOLEJNOSC_CZESTOTLIWOSCI
]
_KLUCZE_WG_ETYKIETY_CZESTOTLIWOSCI = {
    formatowanie.ETYKIETY_CZESTOTLIWOSCI[c]: c for c in formatowanie.KOLEJNOSC_CZESTOTLIWOSCI
}

_DNI_MIESIACA = [str(dzien) for dzien in range(1, 32)]


class FormularzSzablonuCyklicznego(OknoFormularza):
    def __init__(
        self,
        master,
        on_zapisano: Callable[[], None],
        szablon: dict | None = None,
    ):
        super().__init__(master)
        self._tryb_edycji = szablon is not None
        self._szablon_id = szablon["id"] if szablon else None
        self._szablon_zrodlowy = szablon
        self.title("Edytuj szablon cykliczny" if self._tryb_edycji else "Nowy szablon cykliczny")
        self.geometry("760x760")

        self._on_zapisano = on_zapisano
        self._klienci: list[dict] = []
        self._klienci_wg_id: dict[int, dict] = {}
        self._wiersze_pozycji: list[WierszPozycji] = []

        self._etykieta_ladowania = ctk.CTkLabel(
            self, text="Ładowanie...", font=styl.CZCIONKA_TRESC, text_color=styl.KOLOR_TEKST_DRUGORZEDNY
        )
        self._etykieta_ladowania.pack(expand=True)

        uruchom_w_tle(self, self._wczytaj_dane_wstepne, self._po_wczytaniu, self._blad_wczytania)

    # -- ladowanie danych poczatkowych --------------------------------------------------

    def _wczytaj_dane_wstepne(self) -> list[dict]:
        return api_client.pobierz_klientow(tylko_aktywni=True, limit=200)

    def _blad_wczytania(self, e: api_client.ApiError) -> None:
        komunikat_bledu(self, e.komunikat)
        self.destroy()

    def _po_wczytaniu(self, klienci: list[dict]) -> None:
        self._klienci = klienci
        self._klienci_wg_id = {k["id"]: k for k in klienci}
        self._etykieta_ladowania.destroy()
        self._zbuduj_formularz()

    # -- pomocnicze --------------------------------------------------

    def _etykieta_klienta(self, klient: dict) -> str:
        return f"{klient['nazwa']} (#{klient['id']})"

    def _pole(self, master, wiersz: int, kolumna: int, etykieta_tekst: str, widget_fabryka):
        ramka = ctk.CTkFrame(master, fg_color="transparent")
        ramka.grid(
            row=wiersz, column=kolumna, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
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
        return widget

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
        przewijany.grid_columnconfigure(1, weight=1)

        etykiety_klientow = [self._etykieta_klienta(k) for k in self._klienci]
        self._klucze_wg_etykiety_klienta = {
            self._etykieta_klienta(k): k["id"] for k in self._klienci
        }
        self._var_klient = ctk.StringVar(value="")
        self._pole(
            przewijany, 0, 0, "Klient *",
            lambda m: ctk.CTkOptionMenu(
                m,
                values=etykiety_klientow or ["Brak klientów"],
                variable=self._var_klient,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ),
        )

        self._var_typ = ctk.StringVar(value=_ETYKIETY_TYPOW[0])
        self._pole(
            przewijany, 0, 1, "Typ dokumentu *",
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

        self._var_czestotliwosc = ctk.StringVar(value=_ETYKIETY_CZESTOTLIWOSCI[0])
        self._pole(
            przewijany, 1, 0, "Częstotliwość *",
            lambda m: ctk.CTkOptionMenu(
                m,
                values=_ETYKIETY_CZESTOTLIWOSCI,
                variable=self._var_czestotliwosc,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ),
        )

        self._var_dzien = ctk.StringVar(value="1")
        self._pole(
            przewijany, 1, 1, "Dzień generowania (1-31) *",
            lambda m: ctk.CTkOptionMenu(
                m,
                values=_DNI_MIESIACA,
                variable=self._var_dzien,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ),
        )
        ctk.CTkLabel(
            przewijany,
            text=(
                "W miesiącach krótszych niż wybrany dzień (np. 31 w lutym) "
                "faktura wygeneruje się w ostatnim dniu danego miesiąca."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=680,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI))

        dzis = formatowanie.formatuj_date(date.today())
        self._pole_data_poczatku = self._pole(
            przewijany, 3, 0, "Data początku * (DD.MM.RRRR)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_data_poczatku.insert(0, dzis)

        self._pole_data_konca = self._pole(
            przewijany, 3, 1, "Data zakończenia (DD.MM.RRRR, opcjonalnie)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )

        self._pole_waluta = self._pole(
            przewijany, 4, 0, "Waluta (opcjonalnie, domyślnie wg klienta)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )

        # Pozycje
        ramka_pozycji = ctk.CTkFrame(przewijany, fg_color="transparent")
        ramka_pozycji.grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
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
            text="Zapisz szablon",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz,
        )
        self._przycisk_zapisz.grid(row=0, column=1, sticky="ew")
        self.ustaw_akcje_zapisu(self._zapisz, self._przycisk_zapisz)

        if self._tryb_edycji:
            self._wypelnij_z_szablonu(self._szablon_zrodlowy)
        else:
            self._dodaj_wiersz_pozycji()

        self._na_zmiane_typu(self._var_typ.get())
        self.zapamietaj_stan_poczatkowy()

    # -- reakcje na zmiany --------------------------------------------------

    def _na_zmiane_typu(self, etykieta: str) -> None:
        typ = _KLUCZE_WG_ETYKIETY_TYPU.get(etykieta, "faktura_vat")
        ogranicz_do_zw = typ == "rachunek"
        for wiersz in self._wiersze_pozycji:
            wiersz.ustaw_ograniczenie_zw(ogranicz_do_zw)

    # -- pozycje --------------------------------------------------

    def _dodaj_wiersz_pozycji(self) -> None:
        wiersz = WierszPozycji(
            self._kontener_wierszy, on_usun=self._usun_wiersz_pozycji, on_zmiana=lambda: None
        )
        wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        typ_aktualny = _KLUCZE_WG_ETYKIETY_TYPU.get(self._var_typ.get())
        if typ_aktualny == "rachunek":
            wiersz.ustaw_ograniczenie_zw(True)
        self._wiersze_pozycji.append(wiersz)

    def _usun_wiersz_pozycji(self, wiersz: WierszPozycji) -> None:
        wiersz.destroy()
        self._wiersze_pozycji.remove(wiersz)

    # -- tryb edycji: wypelnienie danymi --------------------------------------------------

    def _wypelnij_z_szablonu(self, szablon: dict) -> None:
        klient = self._klienci_wg_id.get(szablon["klient_id"])
        if klient:
            self._var_klient.set(self._etykieta_klienta(klient))

        etykieta_typu = formatowanie.ETYKIETY_TYPU_DOKUMENTU.get(szablon["typ_dokumentu"])
        if etykieta_typu:
            self._var_typ.set(etykieta_typu)

        etykieta_czestotliwosci = formatowanie.ETYKIETY_CZESTOTLIWOSCI.get(szablon["czestotliwosc"])
        if etykieta_czestotliwosci:
            self._var_czestotliwosc.set(etykieta_czestotliwosci)

        self._var_dzien.set(str(szablon["dzien_generowania"]))

        self._pole_data_poczatku.delete(0, "end")
        self._pole_data_poczatku.insert(0, formatowanie.formatuj_date(szablon["data_poczatku"]))
        if szablon.get("data_konca"):
            self._pole_data_konca.delete(0, "end")
            self._pole_data_konca.insert(0, formatowanie.formatuj_date(szablon["data_konca"]))

        self._pole_waluta.delete(0, "end")
        self._pole_waluta.insert(0, szablon["waluta"])

        for pozycja in szablon.get("pozycje", []):
            wiersz = WierszPozycji(
                self._kontener_wierszy, on_usun=self._usun_wiersz_pozycji, on_zmiana=lambda: None
            )
            wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
            wiersz.wczytaj_dane(pozycja)
            self._wiersze_pozycji.append(wiersz)

    # -- zapis --------------------------------------------------

    def _zbierz_i_zwaliduj(self) -> dict | None:
        bledy: list[str] = []

        klient_id = self._klucze_wg_etykiety_klienta.get(self._var_klient.get())
        if klient_id is None:
            bledy.append("Wybierz klienta.")

        typ = _KLUCZE_WG_ETYKIETY_TYPU.get(self._var_typ.get(), "faktura_vat")
        czestotliwosc = _KLUCZE_WG_ETYKIETY_CZESTOTLIWOSCI.get(
            self._var_czestotliwosc.get(), "miesieczna"
        )
        dzien_generowania = int(self._var_dzien.get())

        data_poczatku = None
        try:
            data_poczatku = formatowanie.parsuj_date_pl(self._pole_data_poczatku.get())
        except ValueError as e:
            bledy.append(f"Data początku: {e}")

        data_konca = None
        tekst_data_konca = self._pole_data_konca.get().strip()
        if tekst_data_konca:
            try:
                data_konca = formatowanie.parsuj_date_pl(tekst_data_konca)
            except ValueError as e:
                bledy.append(f"Data zakończenia: {e}")

        if data_poczatku and data_konca and data_konca < data_poczatku:
            bledy.append("Data zakończenia nie może być wcześniejsza niż data początku.")

        waluta = self._pole_waluta.get().strip() or None

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
            "klient_id": klient_id,
            "typ_dokumentu": typ,
            "czestotliwosc": czestotliwosc,
            "dzien_generowania": dzien_generowania,
            "data_poczatku": data_poczatku.isoformat(),
            "pozycje": pozycje_dane,
        }
        if data_konca is not None:
            dane["data_konca"] = data_konca.isoformat()
        if waluta:
            dane["waluta"] = waluta
        return dane

    def _zapisz(self) -> None:
        dane = self._zbierz_i_zwaliduj()
        if dane is None:
            return

        ustaw_tekst_ladowania(self._przycisk_zapisz, True, "Zapisz szablon")

        def zadanie():
            if self._tryb_edycji:
                return api_client.aktualizuj_szablon_cykliczny(self._szablon_id, dane)
            return api_client.utworz_szablon_cykliczny(dane)

        def sukces(wynik: dict) -> None:
            self._on_zapisano()
            klient = self._klienci_wg_id.get(wynik["klient_id"])
            nazwa_klienta = klient["nazwa"] if klient else f"#{wynik['klient_id']}"
            self.destroy()
            pokaz_toast(self.master, f"Szablon cykliczny dla „{nazwa_klienta}” zapisany.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zapisz, False, "Zapisz szablon")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
