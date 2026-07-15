import customtkinter as ctk

from gui import api_client, formatowanie, nastawienia, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.szczegoly_dokumentu_kosztowego import SzczegolyDokumentuKosztowego
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("kontrahent_nazwa", "Kontrahent", 3),
    ("numer_faktury", "Numer faktury", 2),
    ("data_wystawienia", "Data wystawienia", 2),
    ("kwota_brutto", "Kwota brutto", 2),
    ("status", "Status", 2),
]

_KLUCZ_FILTR_STATUS = "filtr_status_dokumentow_kosztowych"


class WidokDokumentowKosztowych(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._dokumenty: list[dict] = []
        self._etykiety_statusow = ["Wszystkie"] + list(
            formatowanie.ETYKIETY_STATUSU_DOKUMENTU_KOSZTOWEGO.values()
        )
        self._klucze_wg_etykiety = {"Wszystkie": None, **{
            v: k for k, v in formatowanie.ETYKIETY_STATUSU_DOKUMENTU_KOSZTOWEGO.items()
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
            text="Dokumenty kosztowe",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            pasek_naglowka,
            text="Status:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=1, padx=(0, styl.ODSTEP_MALY))

        status_zapisany = nastawienia.wczytaj(_KLUCZ_FILTR_STATUS)
        etykieta_startowa = (
            formatowanie.ETYKIETY_STATUSU_DOKUMENTU_KOSZTOWEGO.get(status_zapisany, "Wszystkie")
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
        ).grid(row=0, column=2, padx=(0, styl.ODSTEP_SREDNI))

        self._przycisk_sprawdz = ctk.CTkButton(
            pasek_naglowka,
            text="Sprawdź nowe faktury kosztowe",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._sprawdz_nowe,
        )
        self._przycisk_sprawdz.grid(row=0, column=3)

        self._tabela = Tabela(
            self,
            kolumny=KOLUMNY,
            on_wiersz_kliknij=self._otworz_szczegoly,
            sortowalne=True,
        )
        self._tabela.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(0, styl.ODSTEP_DUZY),
        )

    def _na_zmiane_filtra(self) -> None:
        status_klucz = self._klucze_wg_etykiety.get(self._filtr_var.get())
        nastawienia.zapisz(_KLUCZ_FILTR_STATUS, status_klucz)
        self.odswiez()

    def odswiez(self) -> None:
        status_klucz = self._klucze_wg_etykiety.get(self._filtr_var.get())

        def zadanie():
            return api_client.pobierz_dokumenty_kosztowe(status=status_klucz, limit=200)

        def sukces(dokumenty: list[dict]) -> None:
            self._dokumenty = dokumenty
            self._odswiez_tabele()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _odswiez_tabele(self) -> None:
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
        self._tabela.ustaw_dane(
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
