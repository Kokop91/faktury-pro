import customtkinter as ctk

from gui import api_client, formatowanie, ikony, nastawienia, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_faktury import FormularzFaktury
from gui.windows.szczegoly_faktury import SzczegolyFaktury
from gui.windows.tabela import Tabela

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


class WidokFaktur(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._klienci_wg_id: dict[int, str] = {}
        self._ostatnie_faktury: list[dict] = []
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
        )
        self._tabela.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(0, styl.ODSTEP_DUZY),
        )

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
            faktury = api_client.pobierz_faktury(status=status_klucz, limit=200)
            return klienci, faktury

        def sukces(wynik):
            klienci, faktury = wynik
            self._klienci_wg_id = {k["id"]: k["nazwa"] for k in klienci}
            self._ostatnie_faktury = faktury
            self._odswiez_tabele()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

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
