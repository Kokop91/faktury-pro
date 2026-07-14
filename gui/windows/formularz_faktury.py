from datetime import date, timedelta
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, ikony, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.wiersz_pozycji import WierszPozycji

TYPY_DOKUMENTU_KOLEJNOSC = list(formatowanie.ETYKIETY_TYPU_DOKUMENTU.keys())


class FormularzFaktury(OknoFormularza):
    def __init__(self, master, on_zapisano: Callable[[], None], faktura: dict | None = None):
        super().__init__(master)
        self._tryb_edycji = faktura is not None
        self._faktura_id = faktura["id"] if faktura else None
        self._faktura_zrodlowa = faktura
        self.title("Edytuj fakturę" if self._tryb_edycji else "Nowa faktura")
        self.geometry("940x780")

        self._on_zapisano = on_zapisano
        self._klienci: list[dict] = []
        self._klienci_wg_id: dict[int, dict] = {}
        self._faktury_kandydaci: list[dict] = []
        self._wiersze_pozycji: list[WierszPozycji] = []
        self._termin_platnosci_edytowany_recznie = False
        self._waluta_edytowana_recznie = False
        self._kurs_edytowany_recznie = False
        self._ostatnia_waluta_pobranego_kursu: str | None = None

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
        self._pole_data_wystawienia.bind(
            "<FocusOut>", lambda _z: self._pobierz_kurs_automatycznie()
        )

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
        self._pole_waluta.bind(
            "<FocusOut>", lambda _z: self._pobierz_kurs_automatycznie(), add="+"
        )

        self._pole_kurs = self._pole(
            przewijany, 3, 0, "Kurs waluty",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_kurs.insert(0, "1")
        self._pole_kurs.bind(
            "<KeyRelease>", lambda _z: setattr(self, "_kurs_edytowany_recznie", True)
        )
        self._etykieta_kurs_zrodlo = ctk.CTkLabel(
            self._pole_kurs.master,
            text="",
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        self._etykieta_kurs_zrodlo.pack(fill="x", pady=(2, 0))

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
        ).grid(row=0, column=0, sticky="w", pady=(0, styl.ODSTEP_ETYKIETA))
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
        ).grid(row=0, column=0, sticky="w", pady=(0, styl.ODSTEP_ETYKIETA))
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
        pasek_przyciskow.grid(row=2, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)
        pasek_przyciskow.grid_columnconfigure((0, 1, 2), weight=1)

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
        self.ustaw_akcje_zapisu(
            lambda: self._zapisz(wystaw=False), self._przycisk_robocza
        )

        if self._tryb_edycji:
            self._wypelnij_z_faktury(self._faktura_zrodlowa)
        else:
            self._dodaj_wiersz_pozycji()

        self._na_zmiane_typu(self._var_typ.get())
        self.zapamietaj_stan_poczatkowy()

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
            self._pobierz_kurs_automatycznie()

        self._odswiez_podsumowanie()

    def _pobierz_kurs_automatycznie(self) -> None:
        """Faza 14: pobiera z NBP kurs sredni (tabela A) z ostatniego dnia
        roboczego przed data wystawienia, gdy wybrana jest waluta inna niz
        PLN. Nie nadpisuje kursu wpisanego recznie przez uzytkownika dla TEJ
        SAMEJ waluty - ale zmiana waluty zawsze wyzwala nowe pobranie, bo
        stary kurs (recznie wpisany czy nie) na pewno juz nie pasuje."""
        waluta = self._pole_waluta.get().strip().upper()
        if len(waluta) != 3 or not waluta.isalpha() or waluta == "PLN":
            return

        try:
            data_wystawienia = formatowanie.parsuj_date_pl(self._pole_data_wystawienia.get())
        except ValueError:
            return

        waluta_zmieniona = waluta != self._ostatnia_waluta_pobranego_kursu
        if not waluta_zmieniona and self._kurs_edytowany_recznie:
            return

        def zadanie():
            return api_client.pobierz_kurs_nbp(waluta, data_wystawienia.isoformat())

        def sukces(wynik: dict) -> None:
            self._pole_kurs.delete(0, "end")
            self._pole_kurs.insert(0, wynik["kurs"].replace(".", ","))
            self._kurs_edytowany_recznie = False
            self._ostatnia_waluta_pobranego_kursu = waluta
            data_efektywna = formatowanie.formatuj_date(wynik["data_efektywna"])
            self._etykieta_kurs_zrodlo.configure(
                text=f"Kurs NBP z {data_efektywna}", text_color=styl.KOLOR_TEKST_DRUGORZEDNY
            )

        def blad(e: api_client.ApiError) -> None:
            self._etykieta_kurs_zrodlo.configure(
                text="Brak połączenia z NBP — wpisz kurs ręcznie.",
                text_color=styl.KOLOR_OSTRZEZENIE,
            )

        uruchom_w_tle(self, zadanie, sukces, blad)

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
        wiersz = WierszPozycji(
            self._kontener_wierszy, on_usun=self._usun_wiersz_pozycji, on_zmiana=self._odswiez_podsumowanie
        )
        wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        typ_aktualny = self._klucze_wg_etykiety_typu.get(self._var_typ.get())
        if typ_aktualny == "rachunek":
            wiersz.ustaw_ograniczenie_zw(True)
        self._wiersze_pozycji.append(wiersz)
        self._odswiez_podsumowanie()

    def _usun_wiersz_pozycji(self, wiersz: WierszPozycji) -> None:
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
        self._kurs_edytowany_recznie = True
        self._ostatnia_waluta_pobranego_kursu = faktura["waluta"].upper()

        if faktura.get("przyczyna_korekty"):
            self._pole_przyczyna_korekty.insert("1.0", faktura["przyczyna_korekty"])

        for pozycja in faktura.get("pozycje", []):
            wiersz = WierszPozycji(
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
            self._banner.pokaz("\n".join(bledy))
            return None
        self._banner.ukryj()

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

        def sukces(wynik) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, f"Faktura {wynik['numer']} zapisana.")

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _ustaw_przyciski_aktywne(self, aktywne: bool) -> None:
        ustaw_tekst_ladowania(
            self._przycisk_robocza, not aktywne, "Zapisz jako robocza"
        )
        ustaw_tekst_ladowania(self._przycisk_wystaw, not aktywne, "Wystaw")
