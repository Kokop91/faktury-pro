from datetime import datetime

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.tabela import Tabela

MIESIACE = [
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
]
WARIANTY = {
    "Miesięczny": "miesieczny",
    "Kwartalny": "kwartalny",
    "Roczny": "roczny",
}

KOLUMNY_KUBELKOW = [
    ("seria", "Prognoza", 3),
    ("b0", "Do 30 dni", 2),
    ("b1", "31-60 dni", 2),
    ("b2", "61-90 dni", 2),
    ("b3", "Powyżej 90 dni", 2),
]

KOLUMNY_SZCZEGOLOW_PROGNOZY = [
    ("numer", "Faktura", 2),
    ("klient_nazwa", "Klient", 3),
    ("kwota_pozostala_grosze", "Kwota pozostała", 2),
    ("termin_bazowy", "Termin umowny", 2),
    ("termin_skorygowany", "Termin skorygowany", 2),
]

KOLUMNY_PRODUKTOW = [
    ("nazwa", "Nazwa", 3),
    ("ilosc_sprzedana", "Ilość sprzedana", 2),
    ("przychod_netto_grosze", "Przychód netto", 2),
    ("koszt_grosze", "Koszt", 2),
    ("marza_grosze", "Marża", 2),
    ("marza_procent", "Marża %", 1),
]


class WidokRentownosci(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Rentowność",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(
            row=0, column=0, sticky="w", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI)
        )

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(row=1, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY))
        przewijany.grid_columnconfigure(0, weight=1)

        # -- selektor okresu --------------------------------------------------
        karta_okresu = ctk.CTkFrame(
            przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta_okresu.grid(row=0, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI))
        karta_okresu.grid_columnconfigure((0, 1, 2), weight=1)

        rok_biezacy = datetime.now().year
        lata = [str(r) for r in range(rok_biezacy - 3, rok_biezacy + 2)]

        ctk.CTkLabel(
            karta_okresu, text="Rok:", font=styl.CZCIONKA_ETYKIETA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=0, sticky="w", padx=(styl.ODSTEP_DUZY, 0), pady=(styl.ODSTEP_DUZY, 0))
        self._var_rok = ctk.StringVar(value=str(rok_biezacy))
        ctk.CTkOptionMenu(
            karta_okresu, values=lata, variable=self._var_rok, command=lambda _w: self.odswiez(),
            fg_color=styl.KOLOR_AKCENT, button_color=styl.KOLOR_AKCENT, button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=1, column=0, sticky="ew", padx=(styl.ODSTEP_DUZY, styl.ODSTEP_MALY), pady=(0, styl.ODSTEP_DUZY))

        ctk.CTkLabel(
            karta_okresu, text="Miesiąc:", font=styl.CZCIONKA_ETYKIETA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=1, sticky="w", pady=(styl.ODSTEP_DUZY, 0))
        self._var_miesiac = ctk.StringVar(value=MIESIACE[datetime.now().month - 1])
        self._menu_miesiac = ctk.CTkOptionMenu(
            karta_okresu, values=MIESIACE, variable=self._var_miesiac, command=lambda _w: self.odswiez(),
            fg_color=styl.KOLOR_AKCENT, button_color=styl.KOLOR_AKCENT, button_hover_color=styl.KOLOR_AKCENT_HOVER,
        )
        self._menu_miesiac.grid(row=1, column=1, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_DUZY))

        ctk.CTkLabel(
            karta_okresu, text="Okres:", font=styl.CZCIONKA_ETYKIETA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=2, sticky="w", pady=(styl.ODSTEP_DUZY, 0))
        self._var_wariant = ctk.StringVar(value="Miesięczny")
        ctk.CTkOptionMenu(
            karta_okresu, values=list(WARIANTY.keys()), variable=self._var_wariant,
            command=lambda _w: self._na_zmiane_wariantu(),
            fg_color=styl.KOLOR_AKCENT, button_color=styl.KOLOR_AKCENT, button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=1, column=2, sticky="ew", padx=(styl.ODSTEP_MALY, styl.ODSTEP_DUZY), pady=(0, styl.ODSTEP_DUZY))

        # -- karta marzy --------------------------------------------------
        self._karta_marzy = ctk.CTkFrame(
            przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self._karta_marzy.grid(row=1, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI))

        # -- spodziewane wplywy --------------------------------------------------
        ctk.CTkLabel(
            przewijany, text="Spodziewane wpływy", font=styl.NAGLOWEK_2, text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, styl.ODSTEP_MALY))
        ctk.CTkLabel(
            przewijany,
            text=(
                "Prognoza na podstawie nieopłaconych faktur — „wg terminu umownego” zaklada "
                "zaplate dokladnie w terminie platnosci; „skorygowana” uwzglednia sredni "
                "historyczny czas platnosci danego klienta."
            ),
            font=styl.CZCIONKA_DROBNA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w", justify="left", wraplength=900,
        ).grid(row=3, column=0, sticky="w", pady=(0, styl.ODSTEP_MALY))

        self._tabela_kubelkow = Tabela(przewijany, kolumny=KOLUMNY_KUBELKOW, height=110)
        self._tabela_kubelkow.grid(row=4, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkLabel(
            przewijany, text="Szczegóły należności", font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).grid(row=5, column=0, sticky="w", pady=(0, styl.ODSTEP_MALY))
        self._tabela_szczegolow_prognozy = Tabela(
            przewijany, kolumny=KOLUMNY_SZCZEGOLOW_PROGNOZY, sortowalne=True, height=220
        )
        self._tabela_szczegolow_prognozy.grid(row=6, column=0, sticky="ew", pady=(0, styl.ODSTEP_SREDNI))

        # -- rentownosc produktow --------------------------------------------------
        ctk.CTkLabel(
            przewijany, text="Rentowność produktów/usług", font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).grid(row=7, column=0, sticky="w", pady=(0, styl.ODSTEP_MALY))
        ctk.CTkLabel(
            przewijany,
            text=(
                "Produkty bez ustawionego kosztu zakupu są pomijane (nigdy liczone jako "
                "koszt zerowy) — koszt można ustawić w szczegółach produktu."
            ),
            font=styl.CZCIONKA_DROBNA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w", justify="left", wraplength=900,
        ).grid(row=8, column=0, sticky="w", pady=(0, styl.ODSTEP_MALY))
        self._tabela_produktow = Tabela(
            przewijany, kolumny=KOLUMNY_PRODUKTOW, sortowalne=True, height=260
        )
        self._tabela_produktow.grid(row=9, column=0, sticky="ew")

    def _na_zmiane_wariantu(self) -> None:
        roczny = WARIANTY[self._var_wariant.get()] == "roczny"
        self._menu_miesiac.configure(state="disabled" if roczny else "normal")
        self.odswiez()

    def _wybor(self) -> tuple[int, int | None, str]:
        wariant = WARIANTY[self._var_wariant.get()]
        miesiac = None if wariant == "roczny" else MIESIACE.index(self._var_miesiac.get()) + 1
        return int(self._var_rok.get()), miesiac, wariant

    def odswiez(self) -> None:
        rok, miesiac, wariant = self._wybor()

        def zadanie():
            marza = api_client.pobierz_marze(rok, miesiac, wariant)
            produkty = api_client.pobierz_rentownosc_produktow(rok, miesiac, wariant)
            prognoza = api_client.pobierz_prognoze_wplywow()
            return marza, produkty, prognoza

        def sukces(wynik) -> None:
            marza, produkty, prognoza = wynik
            self._zbuduj_karte_marzy(marza)
            self._zbuduj_tabele_prognozy(prognoza)
            self._zbuduj_tabele_produktow(produkty)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_karte_marzy(self, marza: dict) -> None:
        for dziecko in self._karta_marzy.winfo_children():
            dziecko.destroy()

        if not marza["ma_dane_kosztowe"]:
            ctk.CTkLabel(
                self._karta_marzy,
                text="Brak danych kosztowych za ten okres",
                font=styl.NAGLOWEK_2,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            ).pack(anchor="w", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_MIKRO))
            ctk.CTkLabel(
                self._karta_marzy,
                text=(
                    "Brak dokumentów kosztowych z KSeF i kosztów wprowadzonych ręcznie w "
                    "tym okresie — marża nie jest liczona (nie pokazujemy fałszywego zera)."
                ),
                font=styl.CZCIONKA_DROBNA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                wraplength=800,
                justify="left",
                anchor="w",
            ).pack(anchor="w", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY))
            return

        kolor_marzy = styl.KOLOR_SUKCES if marza["marza_grosze"] >= 0 else styl.KOLOR_BLAD
        wiersze = [
            ("Przychód netto", formatowanie.formatuj_kwote(marza["przychod_netto_grosze"]), None),
            ("Koszty z KSeF", formatowanie.formatuj_kwote(marza["koszty_ksef_grosze"]), None),
            ("Koszty wprowadzone ręcznie", formatowanie.formatuj_kwote(marza["koszty_reczne_grosze"]), None),
            (
                "Marża",
                f"{formatowanie.formatuj_kwote(marza['marza_grosze'])} "
                f"({formatowanie.formatuj_procent(marza['marza_procent'])})",
                kolor_marzy,
            ),
        ]
        for indeks, (etykieta, wartosc, kolor) in enumerate(wiersze):
            wiersz = ctk.CTkFrame(self._karta_marzy, fg_color="transparent")
            wiersz.pack(
                fill="x", padx=styl.ODSTEP_DUZY,
                pady=(styl.ODSTEP_DUZY if indeks == 0 else 2, styl.ODSTEP_DUZY if indeks == len(wiersze) - 1 else 2),
            )
            ctk.CTkLabel(
                wiersz, text=f"{etykieta}:", font=styl.CZCIONKA_ETYKIETA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY, width=220, anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                wiersz, text=wartosc,
                font=styl.CZCIONKA_TRESC_POGRUBIONA if kolor else styl.CZCIONKA_TRESC,
                text_color=kolor or styl.KOLOR_TEKST_GLOWNY, anchor="w",
            ).pack(side="left")

    def _zbuduj_tabele_prognozy(self, prognoza: dict) -> None:
        def wiersz_kubelkow(seria: str, kubelki: list[dict]) -> dict:
            wiersz = {"seria": seria}
            for indeks, kubelek in enumerate(kubelki):
                wiersz[f"b{indeks}"] = kubelek["kwota_grosze"]
            return wiersz

        wiersze_kubelkow = [
            wiersz_kubelkow("Wg terminu umownego", prognoza["kubelki_podstawowe"]),
            wiersz_kubelkow("Skorygowana o historię płatności", prognoza["kubelki_skorygowane"]),
        ]
        formatery_kubelkow = {
            f"b{i}": (lambda w, klucz=f"b{i}": formatowanie.formatuj_kwote(w[klucz])) for i in range(4)
        }
        self._tabela_kubelkow.ustaw_dane(wiersze_kubelkow, formatery=formatery_kubelkow)

        formatery_szczegolow = {
            "kwota_pozostala_grosze": lambda w: formatowanie.formatuj_kwote(
                w["kwota_pozostala_grosze"], w["waluta"]
            ),
            "termin_bazowy": lambda w: formatowanie.formatuj_date(w["termin_bazowy"]),
            "termin_skorygowany": lambda w: formatowanie.formatuj_date(w["termin_skorygowany"]),
        }
        klucze_sortowania_szczegolow = {
            "kwota_pozostala_grosze": lambda w: w["kwota_pozostala_grosze"],
        }
        self._tabela_szczegolow_prognozy.ustaw_dane(
            prognoza["pozycje"],
            formatery=formatery_szczegolow,
            klucze_sortowania=klucze_sortowania_szczegolow,
        )

    def _zbuduj_tabele_produktow(self, produkty: list[dict]) -> None:
        formatery = {
            "ilosc_sprzedana": lambda w: formatowanie.formatuj_ilosc(
                w["ilosc_sprzedana"], w["jednostka_miary"]
            ),
            "przychod_netto_grosze": lambda w: formatowanie.formatuj_kwote(w["przychod_netto_grosze"]),
            "koszt_grosze": lambda w: formatowanie.formatuj_kwote(w["koszt_grosze"]),
            "marza_grosze": lambda w: formatowanie.formatuj_kwote(w["marza_grosze"]),
            "marza_procent": lambda w: formatowanie.formatuj_procent(w["marza_procent"]),
        }
        kolory = {
            "marza_grosze": lambda w: styl.KOLOR_SUKCES if w["marza_grosze"] >= 0 else styl.KOLOR_BLAD,
        }
        klucze_sortowania = {
            "ilosc_sprzedana": lambda w: float(w["ilosc_sprzedana"]),
            "przychod_netto_grosze": lambda w: w["przychod_netto_grosze"],
            "koszt_grosze": lambda w: w["koszt_grosze"],
            "marza_grosze": lambda w: w["marza_grosze"],
        }
        self._tabela_produktow.ustaw_dane(
            produkty, formatery=formatery, kolory=kolory, klucze_sortowania=klucze_sortowania
        )
