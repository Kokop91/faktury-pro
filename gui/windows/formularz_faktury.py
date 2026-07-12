from datetime import date, timedelta
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu

TYPY_DOKUMENTU_KOLEJNOSC = list(formatowanie.ETYKIETY_TYPU_DOKUMENTU.keys())

_ETYKIETY_STAWEK = [
    formatowanie.ETYKIETY_STAWEK_VAT[s] for s in formatowanie.KOLEJNOSC_STAWEK_VAT
]
_KLUCZE_WG_ETYKIETY_STAWKI = {
    formatowanie.ETYKIETY_STAWEK_VAT[s]: s for s in formatowanie.KOLEJNOSC_STAWEK_VAT
}


class _WierszPozycji(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_usun: Callable[["_WierszPozycji"], None],
        on_zmiana: Callable[[], None],
    ):
        super().__init__(master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA)
        self._on_usun = on_usun
        self._on_zmiana = on_zmiana

        for kolumna, waga in enumerate([3, 1, 1, 1, 1, 1, 0]):
            self.grid_columnconfigure(kolumna, weight=waga)

        self.pole_nazwa = ctk.CTkEntry(self, placeholder_text="Nazwa", font=styl.CZCIONKA_TRESC)
        self.pole_nazwa.grid(row=0, column=0, sticky="ew", padx=(styl.ODSTEP_MALY, 4), pady=styl.ODSTEP_MALY)

        self.pole_ilosc = ctk.CTkEntry(self, placeholder_text="Ilość", font=styl.CZCIONKA_TRESC)
        self.pole_ilosc.insert(0, "1")
        self.pole_ilosc.grid(row=0, column=1, sticky="ew", padx=4, pady=styl.ODSTEP_MALY)

        self.pole_jednostka = ctk.CTkEntry(self, placeholder_text="J.m.", font=styl.CZCIONKA_TRESC)
        self.pole_jednostka.insert(0, "szt.")
        self.pole_jednostka.grid(row=0, column=2, sticky="ew", padx=4, pady=styl.ODSTEP_MALY)

        self.pole_cena = ctk.CTkEntry(self, placeholder_text="Cena netto", font=styl.CZCIONKA_TRESC)
        self.pole_cena.grid(row=0, column=3, sticky="ew", padx=4, pady=styl.ODSTEP_MALY)

        self.stawka_var = ctk.StringVar(value=_ETYKIETY_STAWEK[0])
        self.menu_stawka = ctk.CTkOptionMenu(
            self,
            values=_ETYKIETY_STAWEK,
            variable=self.stawka_var,
            command=lambda _wartosc: self._wywolaj_zmiane(),
            width=70,
        )
        self.menu_stawka.grid(row=0, column=4, sticky="ew", padx=4, pady=styl.ODSTEP_MALY)

        self.etykieta_wartosc = ctk.CTkLabel(
            self, text="—", font=styl.CZCIONKA_TRESC, text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="e"
        )
        self.etykieta_wartosc.grid(row=0, column=5, sticky="ew", padx=4)

        ctk.CTkButton(
            self,
            text="✕",
            width=28,
            fg_color="transparent",
            text_color=styl.KOLOR_BLAD,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=lambda: self._on_usun(self),
        ).grid(row=0, column=6, padx=(4, styl.ODSTEP_MALY))

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


class FormularzFaktury(ctk.CTkToplevel):
    def __init__(self, master, on_zapisano: Callable[[], None], faktura: dict | None = None):
        super().__init__(master)
        self._tryb_edycji = faktura is not None
        self._faktura_id = faktura["id"] if faktura else None
        self._faktura_zrodlowa = faktura
        self.title("Edytuj fakturę" if self._tryb_edycji else "Nowa faktura")
        self.geometry("940x780")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()

        self._on_zapisano = on_zapisano
        self._klienci: list[dict] = []
        self._klienci_wg_id: dict[int, dict] = {}
        self._faktury_kandydaci: list[dict] = []
        self._wiersze_pozycji: list[_WierszPozycji] = []
        self._termin_platnosci_edytowany_recznie = False
        self._waluta_edytowana_recznie = False

        self._etykieta_ladowania = ctk.CTkLabel(
            self, text="Ładowanie...", font=styl.CZCIONKA_TRESC, text_color=styl.KOLOR_TEKST_DRUGORZEDNY
        )
        self._etykieta_ladowania.pack(expand=True)

        uruchom_w_tle(self, self._wczytaj_dane_wstepne, self._po_wczytaniu, self._blad_wczytania)

    # -- ladowanie danych poczatkowych --------------------------------------------------

    def _wczytaj_dane_wstepne(self) -> tuple[list[dict], list[dict]]:
        klienci = api_client.pobierz_klientow(tylko_aktywni=False, limit=200)
        faktury = api_client.pobierz_faktury(limit=200)
        return klienci, faktury

    def _blad_wczytania(self, e: api_client.ApiError) -> None:
        komunikat_bledu(self, e.komunikat)
        self.destroy()

    def _po_wczytaniu(self, wynik: tuple[list[dict], list[dict]]) -> None:
        self._klienci, self._faktury_kandydaci = wynik
        self._klienci_wg_id = {k["id"]: k for k in self._klienci}
        self._etykieta_ladowania.destroy()
        self._zbuduj_formularz()

    # -- pomocnicze etykiety --------------------------------------------------

    def _etykieta_klienta(self, klient: dict) -> str:
        return f"{klient['nazwa']} (#{klient['id']})"

    def _etykieta_faktury_kandydata(self, faktura: dict) -> str:
        klient = self._klienci_wg_id.get(faktura["klient_id"])
        nazwa_klienta = klient["nazwa"] if klient else f"#{faktura['klient_id']}"
        return f"{faktura['numer']} — {nazwa_klienta}"

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
        ).pack(fill="x", pady=(0, 2))
        widget = widget_fabryka(ramka)
        widget.pack(fill="x")
        return widget

    # -- budowa formularza --------------------------------------------------

    def _zbuduj_formularz(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(row=0, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0))
        przewijany.grid_columnconfigure(0, weight=1)
        przewijany.grid_columnconfigure(1, weight=1)

        etykiety_klientow = [self._etykieta_klienta(k) for k in self._klienci]
        self._klucze_wg_etykiety_klienta = {
            self._etykieta_klienta(k): k["id"] for k in self._klienci
        }
        self._var_klient = ctk.StringVar(value="")
        self._pole(
            przewijany,
            0,
            0,
            "Klient *",
            lambda m: ctk.CTkOptionMenu(
                m,
                values=etykiety_klientow or ["Brak klientów"],
                variable=self._var_klient,
                command=self._na_zmiane_klienta,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ),
        )

        etykiety_typow = [formatowanie.ETYKIETY_TYPU_DOKUMENTU[t] for t in TYPY_DOKUMENTU_KOLEJNOSC]
        self._klucze_wg_etykiety_typu = {
            formatowanie.ETYKIETY_TYPU_DOKUMENTU[t]: t for t in TYPY_DOKUMENTU_KOLEJNOSC
        }
        self._var_typ = ctk.StringVar(value=etykiety_typow[0])
        self._pole(
            przewijany,
            0,
            1,
            "Typ dokumentu *",
            lambda m: ctk.CTkOptionMenu(
                m,
                values=etykiety_typow,
                variable=self._var_typ,
                command=self._na_zmiane_typu,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ),
        )

        dzis = formatowanie.formatuj_date(date.today())

        self._pole_data_wystawienia = self._pole(
            przewijany, 1, 0, "Data wystawienia * (DD.MM.RRRR)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_data_wystawienia.insert(0, dzis)

        self._pole_data_sprzedazy = self._pole(
            przewijany, 1, 1, "Data sprzedaży * (DD.MM.RRRR)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_data_sprzedazy.insert(0, dzis)

        self._pole_termin_platnosci = self._pole(
            przewijany, 2, 0, "Termin płatności (DD.MM.RRRR, opcjonalnie)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_termin_platnosci.bind(
            "<KeyRelease>", lambda _z: setattr(self, "_termin_platnosci_edytowany_recznie", True)
        )

        self._pole_waluta = self._pole(
            przewijany, 2, 1, "Waluta (opcjonalnie)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_waluta.bind(
            "<KeyRelease>", lambda _z: setattr(self, "_waluta_edytowana_recznie", True)
        )

        self._pole_kurs = self._pole(
            przewijany, 3, 0, "Kurs waluty",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_kurs.insert(0, "1")

        # Dokument powiazany (widoczny tylko dla korygujaca/nota/koncowa)
        self._ramka_dokument_powiazany = ctk.CTkFrame(przewijany, fg_color="transparent")
        self._ramka_dokument_powiazany.grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
        )
        self._ramka_dokument_powiazany.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self._ramka_dokument_powiazany,
            text="Dokument powiązany *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self._var_dokument_powiazany = ctk.StringVar(value="")
        self._klucze_wg_etykiety_dokumentu: dict[str, int] = {}
        self._menu_dokument_powiazany = ctk.CTkOptionMenu(
            self._ramka_dokument_powiazany,
            values=["Brak kandydatów"],
            variable=self._var_dokument_powiazany,
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        )
        self._menu_dokument_powiazany.grid(row=1, column=0, sticky="ew")

        # Przyczyna korekty (widoczna tylko dla korygujaca/nota)
        self._ramka_przyczyna_korekty = ctk.CTkFrame(przewijany, fg_color="transparent")
        self._ramka_przyczyna_korekty.grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
        )
        self._ramka_przyczyna_korekty.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self._ramka_przyczyna_korekty,
            text="Przyczyna korekty *",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self._pole_przyczyna_korekty = ctk.CTkTextbox(
            self._ramka_przyczyna_korekty, height=60, font=styl.CZCIONKA_TRESC
        )
        self._pole_przyczyna_korekty.grid(row=1, column=0, sticky="ew")

        # Pozycje
        self._ramka_pozycji = ctk.CTkFrame(przewijany, fg_color="transparent")
        self._ramka_pozycji.grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
        )
        self._ramka_pozycji.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self._ramka_pozycji, text="Pozycje", font=styl.NAGLOWEK_2, text_color=styl.KOLOR_TEKST_GLOWNY
        ).grid(row=0, column=0, sticky="w", pady=(0, styl.ODSTEP_MALY))
        self._kontener_wierszy = ctk.CTkFrame(self._ramka_pozycji, fg_color="transparent")
        self._kontener_wierszy.grid(row=1, column=0, sticky="ew")
        ctk.CTkButton(
            self._ramka_pozycji,
            text="+ Dodaj pozycję",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._dodaj_wiersz_pozycji,
        ).grid(row=2, column=0, sticky="w", pady=(styl.ODSTEP_MALY, 0))

        # Podglad sum
        podsumowanie = ctk.CTkFrame(
            przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        podsumowanie.grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
        )
        self._etykieta_netto = self._wiersz_podsumowania(podsumowanie, "Razem netto (podgląd)")
        self._etykieta_vat = self._wiersz_podsumowania(podsumowanie, "Razem VAT (podgląd)")
        self._etykieta_brutto = self._wiersz_podsumowania(
            podsumowanie, "Razem brutto (podgląd)", pogrubione=True
        )
        ctk.CTkFrame(podsumowanie, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        # Przyciski akcji - poza przewijanym obszarem, zawsze widoczne
        pasek_przyciskow = ctk.CTkFrame(self, fg_color="transparent")
        pasek_przyciskow.grid(row=1, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)
        pasek_przyciskow.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            pasek_przyciskow,
            text="Anuluj",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_robocza = ctk.CTkButton(
            pasek_przyciskow,
            text="Zapisz jako robocza",
            fg_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            hover_color=styl.KOLOR_TEKST_GLOWNY,
            command=lambda: self._zapisz(wystaw=False),
        )
        self._przycisk_robocza.grid(row=0, column=1, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_wystaw = ctk.CTkButton(
            pasek_przyciskow,
            text="Wystaw",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=lambda: self._zapisz(wystaw=True),
        )
        self._przycisk_wystaw.grid(row=0, column=2, sticky="ew")

        if self._tryb_edycji:
            self._wypelnij_z_faktury(self._faktura_zrodlowa)
        else:
            self._dodaj_wiersz_pozycji()

        self._na_zmiane_typu(self._var_typ.get())

    def _wiersz_podsumowania(self, master, etykieta_tekst: str, pogrubione: bool = False) -> ctk.CTkLabel:
        wiersz = ctk.CTkFrame(master, fg_color="transparent")
        wiersz.pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_MALY, 0))
        ctk.CTkLabel(
            wiersz, text=etykieta_tekst, font=styl.CZCIONKA_TRESC, text_color=styl.KOLOR_TEKST_DRUGORZEDNY
        ).pack(side="left")
        etykieta_wartosci = ctk.CTkLabel(
            wiersz,
            text="—",
            font=styl.CZCIONKA_TRESC_POGRUBIONA if pogrubione else styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        )
        etykieta_wartosci.pack(side="right")
        return etykieta_wartosci

    # -- reakcje na zmiany --------------------------------------------------

    def _na_zmiane_klienta(self, etykieta: str) -> None:
        klient_id = self._klucze_wg_etykiety_klienta.get(etykieta)
        klient = self._klienci_wg_id.get(klient_id) if klient_id is not None else None
        if klient is None:
            return

        if not self._termin_platnosci_edytowany_recznie and not self._pole_termin_platnosci.get().strip():
            try:
                data_wyst = formatowanie.parsuj_date_pl(self._pole_data_wystawienia.get())
            except ValueError:
                data_wyst = date.today()
            termin = data_wyst + timedelta(days=klient.get("domyslny_termin_platnosci_dni", 14))
            self._pole_termin_platnosci.delete(0, "end")
            self._pole_termin_platnosci.insert(0, formatowanie.formatuj_date(termin))

        if not self._waluta_edytowana_recznie and not self._pole_waluta.get().strip():
            self._pole_waluta.delete(0, "end")
            self._pole_waluta.insert(0, klient.get("domyslna_waluta", "PLN"))

        self._odswiez_podsumowanie()

    def _na_zmiane_typu(self, etykieta: str) -> None:
        typ = self._klucze_wg_etykiety_typu.get(etykieta, "faktura_vat")

        wymaga_dokumentu = typ in formatowanie.TYPY_WYMAGAJACE_DOKUMENTU_POWIAZANEGO
        wymaga_przyczyny = typ in formatowanie.TYPY_WYMAGAJACE_PRZYCZYNY_KOREKTY

        if wymaga_dokumentu:
            self._odswiez_kandydatow_dokumentu(typ)
            self._ramka_dokument_powiazany.grid()
        else:
            self._ramka_dokument_powiazany.grid_remove()

        if wymaga_przyczyny:
            self._ramka_przyczyna_korekty.grid()
        else:
            self._ramka_przyczyna_korekty.grid_remove()

        pokazuj_pozycje = typ != "nota_korygujaca"
        if pokazuj_pozycje:
            self._ramka_pozycji.grid()
        else:
            self._ramka_pozycji.grid_remove()

        ogranicz_do_zw = typ == "rachunek"
        for wiersz in self._wiersze_pozycji:
            wiersz.ustaw_ograniczenie_zw(ogranicz_do_zw)

        self._odswiez_podsumowanie()

    def _odswiez_kandydatow_dokumentu(self, typ: str) -> None:
        if typ == "faktura_koncowa":
            dozwolone = {"faktura_zaliczkowa"}
        else:
            dozwolone = formatowanie.DOZWOLONE_TYPY_DOKUMENTU_KORYGOWANEGO

        kandydaci = [
            f
            for f in self._faktury_kandydaci
            if f["typ_dokumentu"] in dozwolone and f["id"] != self._faktura_id
        ]
        etykiety = [self._etykieta_faktury_kandydata(f) for f in kandydaci]
        self._klucze_wg_etykiety_dokumentu = {
            self._etykieta_faktury_kandydata(f): f["id"] for f in kandydaci
        }
        self._menu_dokument_powiazany.configure(values=etykiety or ["Brak kandydatów"])
        if self._var_dokument_powiazany.get() not in self._klucze_wg_etykiety_dokumentu:
            self._var_dokument_powiazany.set(etykiety[0] if etykiety else "")

    # -- pozycje --------------------------------------------------

    def _dodaj_wiersz_pozycji(self) -> None:
        wiersz = _WierszPozycji(
            self._kontener_wierszy, on_usun=self._usun_wiersz_pozycji, on_zmiana=self._odswiez_podsumowanie
        )
        wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        typ_aktualny = self._klucze_wg_etykiety_typu.get(self._var_typ.get())
        if typ_aktualny == "rachunek":
            wiersz.ustaw_ograniczenie_zw(True)
        self._wiersze_pozycji.append(wiersz)
        self._odswiez_podsumowanie()

    def _usun_wiersz_pozycji(self, wiersz: _WierszPozycji) -> None:
        wiersz.destroy()
        self._wiersze_pozycji.remove(wiersz)
        self._odswiez_podsumowanie()

    def _odswiez_podsumowanie(self) -> None:
        netto = vat = brutto = 0
        for wiersz in self._wiersze_pozycji:
            n, v, b = wiersz.podsumowanie_grosze()
            netto += n
            vat += v
            brutto += b
        waluta = self._pole_waluta.get().strip() or "PLN"
        self._etykieta_netto.configure(text=formatowanie.formatuj_kwote(netto, waluta))
        self._etykieta_vat.configure(text=formatowanie.formatuj_kwote(vat, waluta))
        self._etykieta_brutto.configure(text=formatowanie.formatuj_kwote(brutto, waluta))

    # -- tryb edycji: wypelnienie danymi --------------------------------------------------

    def _wypelnij_z_faktury(self, faktura: dict) -> None:
        klient = self._klienci_wg_id.get(faktura["klient_id"])
        if klient:
            self._var_klient.set(self._etykieta_klienta(klient))

        etykieta_typu = formatowanie.ETYKIETY_TYPU_DOKUMENTU.get(faktura["typ_dokumentu"])
        if etykieta_typu:
            self._var_typ.set(etykieta_typu)

        self._pole_data_wystawienia.delete(0, "end")
        self._pole_data_wystawienia.insert(0, formatowanie.formatuj_date(faktura["data_wystawienia"]))
        self._pole_data_sprzedazy.delete(0, "end")
        self._pole_data_sprzedazy.insert(0, formatowanie.formatuj_date(faktura["data_sprzedazy"]))
        self._pole_termin_platnosci.delete(0, "end")
        self._pole_termin_platnosci.insert(0, formatowanie.formatuj_date(faktura["termin_platnosci"]))
        self._termin_platnosci_edytowany_recznie = True
        self._pole_waluta.delete(0, "end")
        self._pole_waluta.insert(0, faktura["waluta"])
        self._waluta_edytowana_recznie = True
        self._pole_kurs.delete(0, "end")
        self._pole_kurs.insert(0, str(faktura["kurs_waluty"]).replace(".", ","))

        if faktura.get("przyczyna_korekty"):
            self._pole_przyczyna_korekty.insert("1.0", faktura["przyczyna_korekty"])

        for pozycja in faktura.get("pozycje", []):
            wiersz = _WierszPozycji(
                self._kontener_wierszy,
                on_usun=self._usun_wiersz_pozycji,
                on_zmiana=self._odswiez_podsumowanie,
            )
            wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
            wiersz.wczytaj_dane(pozycja)
            self._wiersze_pozycji.append(wiersz)

        if faktura.get("dokument_powiazany_id"):
            dopasowana = next(
                (f for f in self._faktury_kandydaci if f["id"] == faktura["dokument_powiazany_id"]),
                None,
            )
            if dopasowana:
                self._var_dokument_powiazany.set(self._etykieta_faktury_kandydata(dopasowana))

    # -- zapis --------------------------------------------------

    def _zbierz_i_zwaliduj(self) -> dict | None:
        bledy: list[str] = []

        klient_id = self._klucze_wg_etykiety_klienta.get(self._var_klient.get())
        if klient_id is None:
            bledy.append("Wybierz klienta.")

        typ = self._klucze_wg_etykiety_typu.get(self._var_typ.get(), "faktura_vat")

        data_wystawienia = None
        try:
            data_wystawienia = formatowanie.parsuj_date_pl(self._pole_data_wystawienia.get())
        except ValueError as e:
            bledy.append(f"Data wystawienia: {e}")

        data_sprzedazy = None
        try:
            data_sprzedazy = formatowanie.parsuj_date_pl(self._pole_data_sprzedazy.get())
        except ValueError as e:
            bledy.append(f"Data sprzedaży: {e}")

        termin_platnosci = None
        termin_tekst = self._pole_termin_platnosci.get().strip()
        if termin_tekst:
            try:
                termin_platnosci = formatowanie.parsuj_date_pl(termin_tekst)
            except ValueError as e:
                bledy.append(f"Termin płatności: {e}")

        waluta = self._pole_waluta.get().strip() or None

        kurs_waluty = None
        try:
            kurs_waluty = formatowanie.parsuj_liczbe_dodatnia(
                self._pole_kurs.get() or "1", "kurs waluty"
            )
        except ValueError as e:
            bledy.append(str(e).capitalize())

        pokazuje_pozycje = typ != "nota_korygujaca"
        pozycje_dane: list[dict] = []
        if pokazuje_pozycje:
            if not self._wiersze_pozycji:
                bledy.append("Dodaj co najmniej jedną pozycję.")
            for indeks, wiersz in enumerate(self._wiersze_pozycji, start=1):
                try:
                    pozycje_dane.append(wiersz.pobierz_dane())
                except ValueError as e:
                    bledy.append(f"Pozycja {indeks}: {e}")

        dokument_powiazany_id = None
        if typ in formatowanie.TYPY_WYMAGAJACE_DOKUMENTU_POWIAZANEGO:
            dokument_powiazany_id = self._klucze_wg_etykiety_dokumentu.get(
                self._var_dokument_powiazany.get()
            )
            if dokument_powiazany_id is None:
                bledy.append("Wybierz dokument powiązany.")

        przyczyna_korekty = None
        if typ in formatowanie.TYPY_WYMAGAJACE_PRZYCZYNY_KOREKTY:
            przyczyna_korekty = self._pole_przyczyna_korekty.get("1.0", "end").strip()
            if not przyczyna_korekty:
                bledy.append("Podaj przyczynę korekty.")

        if bledy:
            komunikat_bledu(self, "\n".join(bledy))
            return None

        dane: dict = {
            "typ_dokumentu": typ,
            "klient_id": klient_id,
            "data_wystawienia": data_wystawienia.isoformat(),
            "data_sprzedazy": data_sprzedazy.isoformat(),
            "kurs_waluty": str(kurs_waluty),
            "pozycje": pozycje_dane,
            "dokument_powiazany_id": dokument_powiazany_id,
            "przyczyna_korekty": przyczyna_korekty,
        }
        if termin_platnosci is not None:
            dane["termin_platnosci"] = termin_platnosci.isoformat()
        if waluta:
            dane["waluta"] = waluta
        return dane

    def _zapisz(self, wystaw: bool) -> None:
        dane = self._zbierz_i_zwaliduj()
        if dane is None:
            return

        self._ustaw_przyciski_aktywne(False)

        def zadanie():
            if self._tryb_edycji:
                wynik = api_client.aktualizuj_fakture(self._faktura_id, dane)
            else:
                wynik = api_client.utworz_fakture(dane)
            if wystaw:
                wynik = api_client.zmien_status_faktury(wynik["id"], "wystawiona")
            return wynik

        def sukces(_wynik) -> None:
            self._on_zapisano()
            self.destroy()

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _ustaw_przyciski_aktywne(self, aktywne: bool) -> None:
        stan = "normal" if aktywne else "disabled"
        self._przycisk_robocza.configure(state=stan)
        self._przycisk_wystaw.configure(state=stan)
