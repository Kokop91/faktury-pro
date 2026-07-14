import customtkinter as ctk

from gui import api_client, ikony, nastawienia, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_klienta import FormularzKlienta
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("nazwa", "Nazwa", 3),
    ("nip", "NIP", 1),
    ("miejscowosc", "Miejscowość", 2),
    ("email", "Email", 2),
    ("telefon", "Telefon", 1),
]

_KLUCZ_SORTOWANIE = "sortowanie_klienci"


class WidokKlientow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._klienci: list[dict] = []

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
            text="Klienci",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w")

        self._pole_szukaj = ctk.CTkEntry(
            pasek_naglowka,
            font=styl.CZCIONKA_TRESC,
            width=220,
            placeholder_text="Szukaj po nazwie...",
        )
        self._pole_szukaj.grid(row=0, column=1, padx=(0, styl.ODSTEP_SREDNI))
        self._pole_szukaj.bind("<KeyRelease>", lambda _z: self._odswiez_tabele())

        ctk.CTkButton(
            pasek_naglowka,
            text="Dodaj klienta",
            image=ikony.ikona_stala("plus"),
            compound="left",
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_formularz,
        ).grid(row=0, column=2)

        sortowanie_zapisane = nastawienia.wczytaj(_KLUCZ_SORTOWANIE)
        sortowanie_poczatkowe = (
            tuple(sortowanie_zapisane) if isinstance(sortowanie_zapisane, list) else None
        )
        self._tabela = Tabela(
            self,
            kolumny=KOLUMNY,
            on_wiersz_kliknij=self._otworz_edycji,
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

    def odswiez(self) -> None:
        def zadanie():
            return api_client.pobierz_klientow(tylko_aktywni=True, limit=200)

        def sukces(klienci: list[dict]) -> None:
            self._klienci = klienci
            self._odswiez_tabele()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _odswiez_tabele(self) -> None:
        szukana_fraza = self._pole_szukaj.get().strip().lower()
        if szukana_fraza:
            klienci = [k for k in self._klienci if szukana_fraza in k["nazwa"].lower()]
        else:
            klienci = self._klienci
        self._tabela.ustaw_dane(klienci)

    def _otworz_formularz(self) -> None:
        FormularzKlienta(self, on_zapisano=self.odswiez)

    def _otworz_edycji(self, wiersz: dict) -> None:
        FormularzKlienta(self, on_zapisano=self.odswiez, klient=wiersz)
