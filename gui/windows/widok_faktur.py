import customtkinter as ctk

from gui import api_client, formatowanie, ikony, nastawienia, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import (
    formatuj_srodowisko_ksef,
    komunikat_bledu,
    komunikat_info,
    potwierdz,
    ustaw_tekst_ladowania,
)
from gui.windows.formularz_faktury import FormularzFaktury
from gui.windows.szczegoly_faktury import SzczegolyFaktury
from gui.windows.tabela import Tabela

# Faktury dla ktorych wysylka zbiorcza ma sens - mirror warunku widocznosci
# przycisku "Wyslij do KSeF" w gui/windows/szczegoly_faktury.py (nie robocza,
# jeszcze nie przyjeta przez KSeF).
def _faktura_wysylalna_do_ksef(wiersz: dict) -> bool:
    return wiersz["status"] != "robocza" and wiersz["status_ksef"] != "przyjeta"

KOLUMNY = [
    ("numer", "Numer", 2),
    ("klient", "Klient", 3),
    ("data_wystawienia", "Data wystawienia", 2),
    ("kwota_brutto", "Kwota brutto", 2),
    ("status", "Status", 2),
    ("status_ksef", "KSeF", 2),
]

_KLUCZ_FILTR_STATUS = "filtr_status_faktur"
_KLUCZ_SORTOWANIE = "sortowanie_faktury"

# GET /faktury zwraca maks. 200 wierszy na zapytanie (limit=200, twardy
# gorny limit walidowany w app/api/faktury.py) - bez doladowywania kolejnych
# stron faktury powyzej tej liczby byly po prostu CICHO niewidoczne w tym
# widoku. "Zaladuj wiecej" dopina kolejna strone do juz wyswietlonej listy
# zamiast pobierac wszystko naraz (dla kilku tysiecy faktur zaladowanie
# wszystkiego jednorazowo zmaterializowaloby dziesiatki tysiecy prawdziwych
# widgetow Tkinter w gui/windows/tabela.py - Tabela nie wirtualizuje wierszy).
LIMIT_STRONY_FAKTUR = 200


class WidokFaktur(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._klienci_wg_id: dict[int, str] = {}
        self._ostatnie_faktury: list[dict] = []
        self._ma_wiecej_faktur = False
        self._srodowisko_ksef = "testowe"
        self._etykiety_statusow = ["Wszystkie"] + list(
            formatowanie.ETYKIETY_STATUSU.values()
        )
        self._klucze_wg_etykiety = {"Wszystkie": None, **{
            v: k for k, v in formatowanie.ETYKIETY_STATUSU.items()
        }}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
        )
        pasek_naglowka.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            pasek_naglowka,
            text="Faktury",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w")

        self._pole_szukaj = ctk.CTkEntry(
            pasek_naglowka,
            font=styl.CZCIONKA_TRESC,
            width=220,
            placeholder_text="Szukaj po numerze lub kliencie...",
        )
        self._pole_szukaj.grid(row=0, column=1, padx=(0, styl.ODSTEP_SREDNI))
        self._pole_szukaj.bind("<KeyRelease>", lambda _z: self._odswiez_tabele())

        ctk.CTkLabel(
            pasek_naglowka,
            text="Status:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=2, padx=(0, styl.ODSTEP_MALY))

        status_zapisany = nastawienia.wczytaj(_KLUCZ_FILTR_STATUS)
        etykieta_startowa = (
            formatowanie.ETYKIETY_STATUSU.get(status_zapisany, "Wszystkie")
            if status_zapisany
            else "Wszystkie"
        )
        self._filtr_var = ctk.StringVar(value=etykieta_startowa)
        ctk.CTkOptionMenu(
            pasek_naglowka,
            values=self._etykiety_statusow,
            variable=self._filtr_var,
            command=lambda _wartosc: self._na_zmiane_filtra(),
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=0, column=3, padx=(0, styl.ODSTEP_SREDNI))

        ctk.CTkButton(
            pasek_naglowka,
            text="Nowa faktura",
            image=ikony.ikona_stala("plus"),
            compound="left",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_formularz,
        ).grid(row=0, column=4)

        # Faza 12D - akcja zbiorcza. Pasek zawsze widoczny (przycisk disabled,
        # gdy nic nie zaznaczono), zeby jego istnienie bylo oczywiste, a nie
        # pojawialo/znikalo w zaleznosci od zaznaczenia.
        pasek_zbiorczy = ctk.CTkFrame(self, fg_color="transparent")
        pasek_zbiorczy.grid(
            row=1, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_MALY)
        )

        self._etykieta_zaznaczonych = ctk.CTkLabel(
            pasek_zbiorczy,
            text="Zaznaczono: 0",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_zaznaczonych.pack(side="left")

        self._przycisk_wyslij_zbiorczo = ctk.CTkButton(
            pasek_zbiorczy,
            text="Wyślij zaznaczone do KSeF",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            state="disabled",
            command=self._wyslij_zaznaczone_do_ksef,
        )
        self._przycisk_wyslij_zbiorczo.pack(side="left", padx=(styl.ODSTEP_SREDNI, 0))

        # Bezpieczenstwo (Faza 12D): zawsze widoczne, do ktorego srodowiska
        # KSeF trafi wysylka zbiorcza - aktualizowane w odswiez().
        self._etykieta_srodowisko = ctk.CTkLabel(
            pasek_zbiorczy, text="", font=styl.CZCIONKA_DROBNA,
            corner_radius=styl.PROMIEN_NAROZNIKA, anchor="w",
        )
        self._etykieta_srodowisko.pack(side="right", ipady=2, ipadx=styl.ODSTEP_MALY)

        sortowanie_zapisane = nastawienia.wczytaj(_KLUCZ_SORTOWANIE)
        sortowanie_poczatkowe = (
            tuple(sortowanie_zapisane) if isinstance(sortowanie_zapisane, list) else None
        )
        self._tabela = Tabela(
            self,
            kolumny=KOLUMNY,
            on_wiersz_kliknij=self._otworz_szczegoly,
            sortowalne=True,
            sortowanie_poczatkowe=sortowanie_poczatkowe,
            on_zmiana_sortowania=lambda klucz, malejaco: nastawienia.zapisz(
                _KLUCZ_SORTOWANIE, [klucz, malejaco]
            ),
            zaznaczalne=True,
            zaznaczalne_dla=_faktura_wysylalna_do_ksef,
            on_zmiana_zaznaczenia=self._na_zmiane_zaznaczenia,
        )
        self._tabela.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(0, styl.ODSTEP_DUZY),
        )

        self._przycisk_wiecej = ctk.CTkButton(
            self,
            text="Załaduj więcej faktur",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._zaladuj_wiecej,
        )
        # Gridowany dopiero w _zaktualizuj_przycisk_wiecej(), gdy faktycznie
        # jest wiecej stron do zaladowania - patrz tam.

    def fokus_wyszukiwania(self) -> None:
        self._pole_szukaj.focus_set()

    def ustaw_filtr_status(self, status_klucz: str | None) -> None:
        """Wywolywane z zewnatrz (np. przez kafelek dashboardu) - ustawia
        dropdown filtra, bez samodzielnego odswiezania (o to dba wolajacy)."""
        etykieta = (
            formatowanie.ETYKIETY_STATUSU.get(status_klucz, "Wszystkie")
            if status_klucz
            else "Wszystkie"
        )
        self._filtr_var.set(etykieta)

    def _na_zmiane_filtra(self) -> None:
        status_klucz = self._klucze_wg_etykiety.get(self._filtr_var.get())
        nastawienia.zapisz(_KLUCZ_FILTR_STATUS, status_klucz)
        self.odswiez()

    def odswiez(self) -> None:
        status_klucz = self._klucze_wg_etykiety.get(self._filtr_var.get())

        def zadanie():
            # tylko_aktywni=False celowo - faktura moze odnosic sie do klienta,
            # ktory zostal miedzyczasie dezaktywowany (soft-delete).
            klienci = api_client.pobierz_klientow(tylko_aktywni=False, limit=200)
            faktury = api_client.pobierz_faktury(
                status=status_klucz, skip=0, limit=LIMIT_STRONY_FAKTUR
            )
            try:
                srodowisko = api_client.pobierz_ustawienia_ksef()["srodowisko"]
            except api_client.ApiError:
                srodowisko = "testowe"
            return klienci, faktury, srodowisko

        def sukces(wynik):
            klienci, faktury, srodowisko = wynik
            self._klienci_wg_id = {k["id"]: k["nazwa"] for k in klienci}
            self._ostatnie_faktury = faktury
            self._ma_wiecej_faktur = len(faktury) == LIMIT_STRONY_FAKTUR
            self._srodowisko_ksef = srodowisko
            self._odswiez_tabele()
            self._zaktualizuj_przycisk_wiecej()
            tekst, kolor_tekstu, kolor_tla = formatuj_srodowisko_ksef(srodowisko)
            self._etykieta_srodowisko.configure(text=tekst, text_color=kolor_tekstu, fg_color=kolor_tla)
            self._na_zmiane_zaznaczenia()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _zaktualizuj_przycisk_wiecej(self) -> None:
        if self._ma_wiecej_faktur:
            self._przycisk_wiecej.grid(
                row=3, column=0, pady=(0, styl.ODSTEP_DUZY)
            )
        else:
            self._przycisk_wiecej.grid_remove()

    def _zaladuj_wiecej(self) -> None:
        status_klucz = self._klucze_wg_etykiety.get(self._filtr_var.get())
        skip = len(self._ostatnie_faktury)

        def zadanie():
            return api_client.pobierz_faktury(
                status=status_klucz, skip=skip, limit=LIMIT_STRONY_FAKTUR
            )

        def sukces(strona: list[dict]) -> None:
            self._ostatnie_faktury = self._ostatnie_faktury + strona
            self._ma_wiecej_faktur = len(strona) == LIMIT_STRONY_FAKTUR
            self._odswiez_tabele()
            self._zaktualizuj_przycisk_wiecej()
            ustaw_tekst_ladowania(self._przycisk_wiecej, False, "Załaduj więcej faktur")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_wiecej, False, "Załaduj więcej faktur")
            komunikat_bledu(self, e.komunikat)

        ustaw_tekst_ladowania(self._przycisk_wiecej, True, "Załaduj więcej faktur", "Ładowanie...")
        uruchom_w_tle(self, zadanie, sukces, blad)

    def _na_zmiane_zaznaczenia(self) -> None:
        liczba = len(self._tabela.pobierz_zaznaczone_id())
        self._etykieta_zaznaczonych.configure(text=f"Zaznaczono: {liczba}")
        self._przycisk_wyslij_zbiorczo.configure(state="normal" if liczba else "disabled")

    def _odswiez_tabele(self) -> None:
        szukana_fraza = self._pole_szukaj.get().strip().lower()
        if szukana_fraza:
            faktury = [
                f
                for f in self._ostatnie_faktury
                if szukana_fraza in f["numer"].lower()
                or szukana_fraza
                in self._klienci_wg_id.get(f["klient_id"], "").lower()
            ]
        else:
            faktury = self._ostatnie_faktury

        formatery = {
            "klient": lambda w: self._klienci_wg_id.get(
                w["klient_id"], f"#{w['klient_id']}"
            ),
            "data_wystawienia": lambda w: formatowanie.formatuj_date(
                w["data_wystawienia"]
            ),
            "kwota_brutto": lambda w: formatowanie.formatuj_kwote(
                w["suma_brutto_grosze"], w["waluta"]
            ),
            "status": lambda w: formatowanie.formatuj_status(
                w["status_efektywny"]
            ),
            "status_ksef": lambda w: formatowanie.formatuj_status_ksef(w["status_ksef"]),
        }
        kolory = {
            "status": lambda w: formatowanie.kolor_statusu(w["status_efektywny"]),
            "status_ksef": lambda w: formatowanie.kolor_statusu_ksef(w["status_ksef"]),
        }
        klucze_sortowania = {
            "klient": lambda w: self._klienci_wg_id.get(w["klient_id"], ""),
            "kwota_brutto": lambda w: w["suma_brutto_grosze"],
            "status": lambda w: w["status_efektywny"],
            "status_ksef": lambda w: w["status_ksef"],
        }
        self._tabela.ustaw_dane(
            faktury, formatery=formatery, kolory=kolory, klucze_sortowania=klucze_sortowania
        )

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        nazwa_klienta = self._klienci_wg_id.get(wiersz["klient_id"])
        SzczegolyFaktury(
            self,
            faktura_id=wiersz["id"],
            nazwa_klienta=nazwa_klienta,
            on_zmiana=self.odswiez,
        )

    def _otworz_formularz(self) -> None:
        FormularzFaktury(self, on_zapisano=self.odswiez)

    def _wyslij_zaznaczone_do_ksef(self) -> None:
        zaznaczone_id = self._tabela.pobierz_zaznaczone_id()
        if not zaznaczone_id:
            return

        # Bezpieczenstwo (Faza 12D): odczytaj srodowisko na nowo TERAZ, tuz
        # przed wysylka, zamiast ufac wartosci zaladowanej przy ostatnim
        # odswiez() - patrz analogiczny komentarz w szczegoly_faktury.py.
        def zadanie_sprawdz():
            try:
                return api_client.pobierz_ustawienia_ksef()["srodowisko"]
            except api_client.ApiError:
                return self._srodowisko_ksef

        def sukces_sprawdz(srodowisko: str) -> None:
            self._srodowisko_ksef = srodowisko
            if srodowisko == "produkcyjne" and not potwierdz(
                self,
                f"Zamierzasz wysłać {len(zaznaczone_id)} faktur(y) do PRODUKCYJNEGO "
                "systemu KSeF, z rzeczywistymi konsekwencjami prawnymi i finansowymi.\n\n"
                "Czy na pewno chcesz kontynuować?",
                tytul="Wysyłka do środowiska produkcyjnego KSeF",
                tekst_tak="Wyślij do produkcji",
                niebezpieczne=True,
            ):
                return
            self._wyslij_zaznaczone_do_ksef_faktycznie(zaznaczone_id)

        def blad_sprawdz(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie_sprawdz, sukces_sprawdz, blad_sprawdz)

    def _wyslij_zaznaczone_do_ksef_faktycznie(self, zaznaczone_id: list) -> None:
        ustaw_tekst_ladowania(
            self._przycisk_wyslij_zbiorczo, True, "Wyślij zaznaczone do KSeF", "Wysyłanie do KSeF..."
        )

        def zadanie():
            return api_client.wyslij_faktury_zbiorczo(zaznaczone_id)

        def sukces(wyniki: list[dict]) -> None:
            ustaw_tekst_ladowania(self._przycisk_wyslij_zbiorczo, False, "Wyślij zaznaczone do KSeF")
            liczba_ok = sum(1 for w in wyniki if w["powodzenie"])
            liczba_wszystkich = len(wyniki)
            if liczba_ok == liczba_wszystkich:
                komunikat_info(self, f"Wysłano pomyślnie {liczba_ok} z {liczba_wszystkich} faktur.")
            else:
                nieudane = [w for w in wyniki if not w["powodzenie"]]
                szczegoly = "\n".join(
                    f"— faktura #{w['faktura_id']}: {w['komunikat']}" for w in nieudane
                )
                komunikat_bledu(
                    self,
                    f"Wysłano pomyślnie {liczba_ok} z {liczba_wszystkich} faktur.\n\n"
                    f"Nieudane:\n{szczegoly}",
                )
            self._tabela.wyczysc_zaznaczenie()
            self._na_zmiane_zaznaczenia()
            self.odswiez()

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_wyslij_zbiorczo, False, "Wyślij zaznaczone do KSeF")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
