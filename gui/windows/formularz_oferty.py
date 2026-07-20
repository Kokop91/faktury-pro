from datetime import date
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, ikony, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.wiersz_pozycji import WierszPozycji


class FormularzOferty(OknoFormularza):
    def __init__(self, master, on_zapisano: Callable[[], None], oferta: dict | None = None):
        super().__init__(master)
        self._tryb_edycji = oferta is not None
        self._oferta_id = oferta["id"] if oferta else None
        self._oferta_zrodlowa = oferta
        self.title("Edytuj ofertę" if self._tryb_edycji else "Nowa oferta")
        self.geometry("820x740")

        self._on_zapisano = on_zapisano
        self._klienci: list[dict] = []
        self._klienci_wg_id: dict[int, dict] = {}
        self._wiersze_pozycji: list[WierszPozycji] = []
        self._waluta_edytowana_recznie = False
        self._kurs_edytowany_recznie = False
        self._ostatnia_waluta_pobranego_kursu: str | None = None

        self._etykieta_ladowania = ctk.CTkLabel(
            self, text="Ładowanie...", font=styl.CZCIONKA_TRESC, text_color=styl.KOLOR_TEKST_DRUGORZEDNY
        )
        self._etykieta_ladowania.pack(expand=True)

        uruchom_w_tle(self, self._wczytaj_dane_wstepne, self._po_wczytaniu, self._blad_wczytania)

    # -- ladowanie danych poczatkowych --------------------------------------------------

    def _wczytaj_dane_wstepne(self) -> list[dict]:
        return api_client.pobierz_klientow(tylko_aktywni=False, limit=200)

    def _blad_wczytania(self, e: api_client.ApiError) -> None:
        komunikat_bledu(self, e.komunikat)
        self.destroy()

    def _po_wczytaniu(self, klienci: list[dict]) -> None:
        self._klienci = klienci
        self._klienci_wg_id = {k["id"]: k for k in self._klienci}
        self._etykieta_ladowania.destroy()
        self._zbuduj_formularz()

    # -- pomocnicze etykiety --------------------------------------------------

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

        dzis = formatowanie.formatuj_date(date.today())

        self._pole_data_wystawienia = self._pole(
            przewijany, 0, 1, "Data wystawienia * (DD.MM.RRRR)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_data_wystawienia.insert(0, dzis)
        self._pole_data_wystawienia.bind(
            "<FocusOut>", lambda _z: self._pobierz_kurs_automatycznie()
        )

        self._pole_data_waznosci = self._pole(
            przewijany, 1, 0, "Oferta ważna do * (DD.MM.RRRR)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )

        self._pole_waluta = self._pole(
            przewijany, 1, 1, "Waluta (opcjonalnie)",
            lambda m: ctk.CTkEntry(m, font=styl.CZCIONKA_TRESC),
        )
        self._pole_waluta.bind(
            "<KeyRelease>", lambda _z: setattr(self, "_waluta_edytowana_recznie", True)
        )
        self._pole_waluta.bind(
            "<FocusOut>", lambda _z: self._pobierz_kurs_automatycznie(), add="+"
        )

        self._pole_kurs = self._pole(
            przewijany, 2, 0, "Kurs waluty",
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

        # Pozycje
        ramka_pozycji = ctk.CTkFrame(przewijany, fg_color="transparent")
        ramka_pozycji.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
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

        # Podglad sum
        podsumowanie = ctk.CTkFrame(
            przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        podsumowanie.grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI)
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
            command=lambda: self._zapisz(wyslij=False),
        )
        self._przycisk_robocza.grid(row=0, column=1, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_wyslij = ctk.CTkButton(
            pasek_przyciskow,
            text="Wyślij",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=lambda: self._zapisz(wyslij=True),
        )
        self._przycisk_wyslij.grid(row=0, column=2, sticky="ew")
        self.ustaw_akcje_zapisu(
            lambda: self._zapisz(wyslij=False), self._przycisk_robocza
        )

        if self._tryb_edycji:
            self._wypelnij_z_oferty(self._oferta_zrodlowa)
        else:
            self._pole_data_waznosci.insert(0, dzis)
            self._dodaj_wiersz_pozycji()

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

        if not self._waluta_edytowana_recznie and not self._pole_waluta.get().strip():
            self._pole_waluta.delete(0, "end")
            self._pole_waluta.insert(0, klient.get("domyslna_waluta", "PLN"))
            self._pobierz_kurs_automatycznie()

        self._odswiez_podsumowanie()

    def _pobierz_kurs_automatycznie(self) -> None:
        """Mirror formularz_faktury.py:_pobierz_kurs_automatycznie (Faza 14) -
        pobiera z NBP kurs sredni z ostatniego dnia roboczego przed data
        wystawienia, gdy wybrana jest waluta inna niz PLN."""
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

    # -- pozycje --------------------------------------------------

    def _dodaj_wiersz_pozycji(self) -> None:
        wiersz = WierszPozycji(
            self._kontener_wierszy, on_usun=self._usun_wiersz_pozycji, on_zmiana=self._odswiez_podsumowanie
        )
        wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
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

    def _wypelnij_z_oferty(self, oferta: dict) -> None:
        klient = self._klienci_wg_id.get(oferta["klient_id"])
        if klient:
            self._var_klient.set(self._etykieta_klienta(klient))

        self._pole_data_wystawienia.delete(0, "end")
        self._pole_data_wystawienia.insert(0, formatowanie.formatuj_date(oferta["data_wystawienia"]))
        self._pole_data_waznosci.delete(0, "end")
        self._pole_data_waznosci.insert(0, formatowanie.formatuj_date(oferta["data_waznosci"]))
        self._pole_waluta.delete(0, "end")
        self._pole_waluta.insert(0, oferta["waluta"])
        self._waluta_edytowana_recznie = True
        self._pole_kurs.delete(0, "end")
        self._pole_kurs.insert(0, str(oferta["kurs_waluty"]).replace(".", ","))
        self._kurs_edytowany_recznie = True
        self._ostatnia_waluta_pobranego_kursu = oferta["waluta"].upper()

        for pozycja in oferta.get("pozycje", []):
            wiersz = WierszPozycji(
                self._kontener_wierszy,
                on_usun=self._usun_wiersz_pozycji,
                on_zmiana=self._odswiez_podsumowanie,
            )
            wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
            wiersz.wczytaj_dane(pozycja)
            self._wiersze_pozycji.append(wiersz)

        self._odswiez_podsumowanie()

    # -- zapis --------------------------------------------------

    def _zbierz_i_zwaliduj(self) -> dict | None:
        bledy: list[str] = []

        klient_id = self._klucze_wg_etykiety_klienta.get(self._var_klient.get())
        if klient_id is None:
            bledy.append("Wybierz klienta.")

        data_wystawienia = None
        try:
            data_wystawienia = formatowanie.parsuj_date_pl(self._pole_data_wystawienia.get())
        except ValueError as e:
            bledy.append(f"Data wystawienia: {e}")

        data_waznosci = None
        try:
            data_waznosci = formatowanie.parsuj_date_pl(self._pole_data_waznosci.get())
        except ValueError as e:
            bledy.append(f"Oferta ważna do: {e}")

        waluta = self._pole_waluta.get().strip().upper() or None
        if waluta is not None and (len(waluta) != 3 or not waluta.isalpha()):
            bledy.append("Waluta musi być trzyliterowym kodem (np. PLN, EUR, USD).")

        kurs_waluty = None
        try:
            kurs_waluty = formatowanie.parsuj_liczbe_dodatnia(
                self._pole_kurs.get() or "1", "kurs waluty"
            )
        except ValueError as e:
            bledy.append(str(e).capitalize())

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
            "data_wystawienia": data_wystawienia.isoformat(),
            "data_waznosci": data_waznosci.isoformat(),
            "kurs_waluty": str(kurs_waluty),
            "pozycje": pozycje_dane,
        }
        if waluta:
            dane["waluta"] = waluta
        return dane

    def _zapisz(self, wyslij: bool) -> None:
        dane = self._zbierz_i_zwaliduj()
        if dane is None:
            return

        self._ustaw_przyciski_aktywne(False)

        def zadanie():
            if self._tryb_edycji:
                wynik = api_client.aktualizuj_oferte(self._oferta_id, dane)
            else:
                wynik = api_client.utworz_oferte(dane)
            if wyslij:
                wynik = api_client.zmien_status_oferty(wynik["id"], "wyslana")
            return wynik

        def sukces(wynik) -> None:
            self._on_zapisano()
            self.destroy()
            pokaz_toast(self.master, f"Oferta {wynik['numer']} zapisana.")

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _ustaw_przyciski_aktywne(self, aktywne: bool) -> None:
        ustaw_tekst_ladowania(
            self._przycisk_robocza, not aktywne, "Zapisz jako robocza"
        )
        ustaw_tekst_ladowania(self._przycisk_wyslij, not aktywne, "Wyślij")
