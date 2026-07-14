import customtkinter as ctk

from gui import api_client, formatowanie, ikony, nastawienia, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.formularz_szablonu_cyklicznego import FormularzSzablonuCyklicznego
from gui.windows.szczegoly_szablonu_cyklicznego import SzczegolySzablonuCyklicznego
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("klient", "Klient", 3),
    ("czestotliwosc", "Częstotliwość", 2),
    ("nastepny_termin", "Następny termin", 2),
    ("status", "Status", 1),
    ("kwota", "Kwota (szacowana)", 2),
]

_KLUCZ_SORTOWANIE = "sortowanie_szablony_cykliczne"


class WidokFakturCyklicznych(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._klienci_wg_id: dict[int, str] = {}
        self._szablony: list[dict] = []

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
            text="Faktury cykliczne",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w")

        self._pole_szukaj = ctk.CTkEntry(
            pasek_naglowka,
            font=styl.CZCIONKA_TRESC,
            width=220,
            placeholder_text="Szukaj po kliencie...",
        )
        self._pole_szukaj.grid(row=0, column=1, padx=(0, styl.ODSTEP_SREDNI))
        self._pole_szukaj.bind("<KeyRelease>", lambda _z: self._odswiez_tabele())

        ctk.CTkButton(
            pasek_naglowka,
            text="Nowy szablon",
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

    def odswiez(self) -> None:
        def zadanie():
            klienci = api_client.pobierz_klientow(tylko_aktywni=False, limit=200)
            szablony = api_client.pobierz_szablony_cykliczne()
            return klienci, szablony

        def sukces(wynik) -> None:
            klienci, szablony = wynik
            self._klienci_wg_id = {k["id"]: k["nazwa"] for k in klienci}
            self._szablony = szablony
            self._odswiez_tabele()

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad, wskaznik=self._tabela)

    def _odswiez_tabele(self) -> None:
        szukana_fraza = self._pole_szukaj.get().strip().lower()
        if szukana_fraza:
            szablony = [
                s for s in self._szablony
                if szukana_fraza in self._klienci_wg_id.get(s["klient_id"], "").lower()
            ]
        else:
            szablony = self._szablony

        formatery = {
            "klient": lambda s: self._klienci_wg_id.get(
                s["klient_id"], f"#{s['klient_id']}"
            ),
            "czestotliwosc": lambda s: formatowanie.formatuj_czestotliwosc(s["czestotliwosc"]),
            "nastepny_termin": lambda s: (
                formatowanie.formatuj_date(s["nastepny_termin"])
                if s.get("nastepny_termin")
                else "—"
            ),
            "status": lambda s: formatowanie.formatuj_status_szablonu(s["status"]),
            "kwota": lambda s: formatowanie.formatuj_kwote(
                s["suma_brutto_szacowana_grosze"], s["waluta"]
            ),
        }
        kolory = {
            "status": lambda s: formatowanie.kolor_statusu_szablonu(s["status"]),
        }
        klucze_sortowania = {
            "klient": lambda s: self._klienci_wg_id.get(s["klient_id"], ""),
            "czestotliwosc": lambda s: s["czestotliwosc"],
            "nastepny_termin": lambda s: s.get("nastepny_termin") or "",
            "kwota": lambda s: s["suma_brutto_szacowana_grosze"],
        }
        self._tabela.ustaw_dane(
            szablony, formatery=formatery, kolory=kolory, klucze_sortowania=klucze_sortowania
        )

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        SzczegolySzablonuCyklicznego(self, szablon_id=wiersz["id"], on_zmiana=self.odswiez)

    def _otworz_formularz(self) -> None:
        FormularzSzablonuCyklicznego(self, on_zapisano=self.odswiez)
