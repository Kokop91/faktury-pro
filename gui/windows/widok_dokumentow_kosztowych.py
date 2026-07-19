import customtkinter as ctk

from gui import api_client, formatowanie, nastawienia, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import (
    formatuj_srodowisko_ksef,
    komunikat_bledu,
    pokaz_toast,
    ustaw_tekst_ladowania,
)
from gui.windows.formularz_kosztu_recznego import FormularzKosztuRecznego
from gui.windows.szczegoly_dokumentu_kosztowego import SzczegolyDokumentuKosztowego
from gui.windows.tabela import Tabela

KOLUMNY_KSEF = [
    ("kontrahent_nazwa", "Kontrahent", 3),
    ("numer_faktury", "Numer faktury", 2),
    ("data_wystawienia", "Data wystawienia", 2),
    ("kwota_brutto", "Kwota brutto", 2),
    ("status", "Status", 2),
]

KOLUMNY_RECZNE = [
    ("data", "Data", 2),
    ("kategoria", "Kategoria", 2),
    ("kwota", "Kwota", 2),
    ("opis", "Opis", 3),
]

_KLUCZ_FILTR_STATUS = "filtr_status_dokumentow_kosztowych"
_ZAKLADKA_KSEF = "Z KSeF"
_ZAKLADKA_RECZNE = "Wprowadzone ręcznie"


class WidokDokumentowKosztowych(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._dokumenty: list[dict] = []
        self._koszty_reczne: list[dict] = []
        self._etykiety_statusow = ["Wszystkie"] + list(
            formatowanie.ETYKIETY_STATUSU_DOKUMENTU_KOSZTOWEGO.values()
        )
        self._klucze_wg_etykiety = {"Wszystkie": None, **{
            v: k for k, v in formatowanie.ETYKIETY_STATUSU_DOKUMENTU_KOSZTOWEGO.items()
        }}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
        )
        pasek_naglowka.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            pasek_naglowka, text="Dokumenty kosztowe", font=styl.NAGLOWEK_1, text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w")

        self._var_zakladka = ctk.StringVar(value=_ZAKLADKA_KSEF)
        ctk.CTkSegmentedButton(
            pasek_naglowka,
            values=[_ZAKLADKA_KSEF, _ZAKLADKA_RECZNE],
            variable=self._var_zakladka,
            command=lambda _w: self._na_zmiane_zakladki(),
            fg_color=styl.KOLOR_KARTA,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
            unselected_color=styl.KOLOR_KARTA,
        ).grid(row=0, column=1)

        # -- pasek narzedzi zakladki "Z KSeF" --------------------------------------------------
        self._pasek_ksef = ctk.CTkFrame(self, fg_color="transparent")
        self._pasek_ksef.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._pasek_ksef, text="Status:", font=styl.CZCIONKA_ETYKIETA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=1, padx=(0, styl.ODSTEP_MALY))

        status_zapisany = nastawienia.wczytaj(_KLUCZ_FILTR_STATUS)
        etykieta_startowa = (
            formatowanie.ETYKIETY_STATUSU_DOKUMENTU_KOSZTOWEGO.get(status_zapisany, "Wszystkie")
            if status_zapisany
            else "Wszystkie"
        )
        self._filtr_var = ctk.StringVar(value=etykieta_startowa)
        ctk.CTkOptionMenu(
            self._pasek_ksef, values=self._etykiety_statusow, variable=self._filtr_var,
            command=lambda _wartosc: self._na_zmiane_filtra(),
            fg_color=styl.KOLOR_AKCENT, button_color=styl.KOLOR_AKCENT, button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=0, column=2, padx=(0, styl.ODSTEP_SREDNI))

        self._przycisk_sprawdz = ctk.CTkButton(
            self._pasek_ksef, text="Sprawdź nowe faktury kosztowe", font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT, hover_color=styl.KOLOR_AKCENT_HOVER, command=self._sprawdz_nowe,
        )
        self._przycisk_sprawdz.grid(row=0, column=3)

        # Bezpieczenstwo (Faza 12D): zawsze widoczne, do ktorego srodowiska
        # KSeF trafi zapytanie o nowe faktury - aktualizowane przy kazdym
        # odswiezeniu (patrz odswiez()), nie tylko raz przy starcie.
        self._etykieta_srodowisko = ctk.CTkLabel(
            self._pasek_ksef, text="", font=styl.CZCIONKA_DROBNA,
            corner_radius=styl.PROMIEN_NAROZNIKA, anchor="w",
        )
        self._etykieta_srodowisko.grid(row=0, column=4, padx=(styl.ODSTEP_MALY, 0), ipady=2, ipadx=styl.ODSTEP_MALY)

        # -- pasek narzedzi zakladki "Wprowadzone recznie" --------------------------------------------------
        self._pasek_reczne = ctk.CTkFrame(self, fg_color="transparent")
        self._pasek_reczne.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            self._pasek_reczne, text="Dodaj koszt", font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT, hover_color=styl.KOLOR_AKCENT_HOVER, command=self._dodaj_koszt_reczny,
        ).grid(row=0, column=1)

        # -- tabele --------------------------------------------------
        self._tabela_ksef = Tabela(
            self, kolumny=KOLUMNY_KSEF, on_wiersz_kliknij=self._otworz_szczegoly, sortowalne=True,
        )
        self._tabela_reczne = Tabela(
            self, kolumny=KOLUMNY_RECZNE, on_wiersz_kliknij=self._otworz_koszt_reczny, sortowalne=True,
        )

        self._pokaz_zakladke(odswiez_dane=False)

    def _na_zmiane_zakladki(self) -> None:
        self._pokaz_zakladke()

    def _pokaz_zakladke(self, odswiez_dane: bool = True) -> None:
        aktywna = self._var_zakladka.get()
        if aktywna == _ZAKLADKA_KSEF:
            self._pasek_reczne.grid_remove()
            self._tabela_reczne.grid_remove()
            self._pasek_ksef.grid(
                row=1, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_MALY)
            )
            self._tabela_ksef.grid(
                row=2, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
            )
        else:
            self._pasek_ksef.grid_remove()
            self._tabela_ksef.grid_remove()
            self._pasek_reczne.grid(
                row=1, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_MALY)
            )
            self._tabela_reczne.grid(
                row=2, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
            )
        if odswiez_dane:
            self.odswiez()

    def _na_zmiane_filtra(self) -> None:
        status_klucz = self._klucze_wg_etykiety.get(self._filtr_var.get())
        nastawienia.zapisz(_KLUCZ_FILTR_STATUS, status_klucz)
        self.odswiez()

    def odswiez(self) -> None:
        if self._var_zakladka.get() == _ZAKLADKA_KSEF:
            self._odswiez_ksef()
        else:
            self._odswiez_reczne()

    def _odswiez_ksef(self) -> None:
        status_klucz = self._klucze_wg_etykiety.get(self._filtr_var.get())

        def zadanie():
            dokumenty = api_client.pobierz_dokumenty_kosztowe(status=status_klucz, limit=200)
            try:
                srodowisko = api_client.pobierz_ustawienia_ksef()["srodowisko"]
            except api_client.ApiError:
                srodowisko = "testowe"
            return dokumenty, srodowisko

        def sukces(wynik) -> None:
            dokumenty, srodowisko = wynik
            self._dokumenty = dokumenty
            self._odswiez_tabele_ksef()
            tekst, kolor_tekstu, kolor_tla = formatuj_srodowisko_ksef(srodowisko)
            self._etykieta_srodowisko.configure(text=tekst, text_color=kolor_tekstu, fg_color=kolor_tla)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela_ksef)

    def _odswiez_tabele_ksef(self) -> None:
        formatery = {
            "kontrahent_nazwa": lambda w: w.get("kontrahent_nazwa") or f"NIP {w.get('kontrahent_nip') or '?'}",
            "data_wystawienia": lambda w: formatowanie.formatuj_date(w["data_wystawienia"]),
            "kwota_brutto": lambda w: formatowanie.formatuj_kwote(w["brutto_grosze"], w["waluta"]),
            "status": lambda w: formatowanie.formatuj_status_dokumentu_kosztowego(w["status"]),
        }
        kolory = {
            "status": lambda w: formatowanie.kolor_statusu_dokumentu_kosztowego(w["status"]),
        }
        klucze_sortowania = {
            "kwota_brutto": lambda w: w["brutto_grosze"],
            "status": lambda w: w["status"],
        }
        self._tabela_ksef.ustaw_dane(
            self._dokumenty, formatery=formatery, kolory=kolory, klucze_sortowania=klucze_sortowania
        )

    def _sprawdz_nowe(self) -> None:
        ustaw_tekst_ladowania(
            self._przycisk_sprawdz, True, "Sprawdź nowe faktury kosztowe", "Sprawdzanie w KSeF..."
        )

        def zadanie():
            return api_client.pobierz_nowe_koszty_ksef()

        def sukces(wynik: dict) -> None:
            ustaw_tekst_ladowania(self._przycisk_sprawdz, False, "Sprawdź nowe faktury kosztowe")
            if wynik["powodzenie"]:
                pokaz_toast(self, wynik["komunikat"])
                if wynik["liczba_nowych"]:
                    self.odswiez()
            else:
                komunikat_bledu(self, wynik["komunikat"])

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_sprawdz, False, "Sprawdź nowe faktury kosztowe")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        SzczegolyDokumentuKosztowego(self, dokument_id=wiersz["id"], on_zmiana=self.odswiez)

    # -- zakladka "Wprowadzone recznie" --------------------------------------------------

    def _odswiez_reczne(self) -> None:
        def zadanie():
            return api_client.pobierz_koszty_reczne(limit=200)

        def sukces(koszty: list[dict]) -> None:
            self._koszty_reczne = koszty
            self._odswiez_tabele_reczne()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela_reczne)

    def _odswiez_tabele_reczne(self) -> None:
        formatery = {
            "data": lambda w: formatowanie.formatuj_date(w["data"]),
            "kwota": lambda w: formatowanie.formatuj_kwote(w["kwota_grosze"]),
            "opis": lambda w: w.get("opis") or "",
        }
        klucze_sortowania = {
            "kwota": lambda w: w["kwota_grosze"],
        }
        self._tabela_reczne.ustaw_dane(
            self._koszty_reczne, formatery=formatery, klucze_sortowania=klucze_sortowania
        )

    def _dodaj_koszt_reczny(self) -> None:
        FormularzKosztuRecznego(self, on_zapisano=self.odswiez)

    def _otworz_koszt_reczny(self, wiersz: dict) -> None:
        FormularzKosztuRecznego(self, on_zapisano=self.odswiez, koszt=wiersz)
