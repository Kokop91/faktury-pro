from datetime import date
from typing import Callable

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.szczegoly_faktury import SzczegolyFaktury
from gui.windows.szczegoly_produktu import SzczegolyProduktu

_NAZWY_MIESIECY = [
    "Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
    "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru",
]


def _kolor(wartosc):
    """Rozwiazuje krotke (jasny, ciemny) ze styl.py do pojedynczego koloru
    zgodnego z aktualnym trybem wygladu - w odroznieniu od widgetow CTk,
    matplotlib nie obsluguje takich krotek natywnie."""
    if isinstance(wartosc, tuple):
        return wartosc[1] if ctk.get_appearance_mode() == "Dark" else wartosc[0]
    return wartosc


class _Kafelek(ctk.CTkFrame):
    def __init__(
        self,
        master,
        tytul: str,
        wartosc: str,
        podtytul: str | None,
        kolor_wartosci,
        on_klik: Callable[[], None],
    ):
        super().__init__(
            master,
            fg_color=styl.KOLOR_KARTA,
            corner_radius=styl.PROMIEN_NAROZNIKA,
            cursor="hand2",
        )

        widgety = [self]

        etykieta_tytul = ctk.CTkLabel(
            self,
            text=tytul,
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        etykieta_tytul.pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, 0))
        widgety.append(etykieta_tytul)

        etykieta_wartosc = ctk.CTkLabel(
            self,
            text=wartosc,
            font=styl.NAGLOWEK_KAFELEK,
            text_color=kolor_wartosci or styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        )
        etykieta_wartosc.pack(fill="x", padx=styl.ODSTEP_SREDNI)
        widgety.append(etykieta_wartosc)

        if podtytul:
            etykieta_podtytul = ctk.CTkLabel(
                self,
                text=podtytul,
                font=styl.CZCIONKA_DROBNA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                anchor="w",
            )
            etykieta_podtytul.pack(
                fill="x", padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_SREDNI)
            )
            widgety.append(etykieta_podtytul)
        else:
            ctk.CTkFrame(self, fg_color="transparent", height=styl.ODSTEP_SREDNI).pack()

        for widget in widgety:
            widget.bind("<Button-1>", lambda _zdarzenie: on_klik())


class _WierszUwagi(ctk.CTkFrame):
    def __init__(
        self,
        master,
        lewy_tekst: str,
        prawy_tekst: str,
        kolor_prawego,
        on_klik: Callable[[], None],
    ):
        super().__init__(
            master,
            fg_color=styl.KOLOR_KARTA,
            corner_radius=styl.PROMIEN_NAROZNIKA,
            cursor="hand2",
        )
        self.grid_columnconfigure(0, weight=1)

        etykieta_lewa = ctk.CTkLabel(
            self,
            text=lewy_tekst,
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        )
        etykieta_lewa.grid(
            row=0, column=0, sticky="w", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY
        )

        etykieta_prawa = ctk.CTkLabel(
            self,
            text=prawy_tekst,
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=kolor_prawego,
            anchor="e",
        )
        etykieta_prawa.grid(
            row=0, column=1, sticky="e", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY
        )

        for widget in (self, etykieta_lewa, etykieta_prawa):
            widget.bind("<Button-1>", lambda _zdarzenie: on_klik())


class WidokDashboard(ctk.CTkFrame):
    def __init__(self, master, on_nawigacja: Callable[..., None]):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.on_nawigacja = on_nawigacja
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._kafelki: list[_Kafelek] = []
        self._kafelki_ksef: list[_Kafelek] = []
        self._wiersze_uwagi: list[ctk.CTkBaseClass] = []
        self._ostatni_wykres: list[dict] | None = None

        ctk.CTkLabel(
            self,
            text="Dashboard",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
        )

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(
            row=1, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
        )
        przewijany.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kafelki")
        self._ramka_kafelkow = przewijany

        ctk.CTkLabel(
            przewijany,
            text="KSeF",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        self._ramka_kafelkow_ksef = ctk.CTkFrame(przewijany, fg_color="transparent")
        self._ramka_kafelkow_ksef.grid(row=2, column=0, columnspan=4, sticky="ew")
        self._ramka_kafelkow_ksef.grid_columnconfigure((0, 1), weight=1, uniform="kafelki_ksef")

        self._karta_wykresu = ctk.CTkFrame(
            przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self._karta_wykresu.grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=(styl.ODSTEP_SREDNI, 0)
        )
        self._karta_wykresu.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._karta_wykresu,
            text="Przychody — ostatnie 12 miesięcy",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, 0))

        self._figura = Figure(figsize=(8, 3), dpi=100)
        self._osie = self._figura.add_subplot(111)
        self._platno = FigureCanvasTkAgg(self._figura, master=self._karta_wykresu)
        self._widget_platna = self._platno.get_tk_widget()
        self._widget_platna.grid(
            row=1, column=0, sticky="nsew", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_SREDNI
        )

        self._etykieta_brak_wykresu = ctk.CTkLabel(
            self._karta_wykresu,
            text="Brak danych — wystaw pierwszą fakturę.",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )

        ctk.CTkLabel(
            przewijany,
            text="Wymagają uwagi",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        self._ramka_uwagi = ctk.CTkFrame(przewijany, fg_color="transparent")
        self._ramka_uwagi.grid(row=5, column=0, columnspan=4, sticky="ew")
        self._ramka_uwagi.grid_columnconfigure(0, weight=1)

        # Przerysowanie wykresu przy zmianie trybu jasny/ciemny - customtkinter
        # sam odswieza kolory widgetow CTk, ale matplotlib nie jest widgetem CTk
        # i wymaga recznego przerysowania z nowa paleta kolorow.
        ctk.AppearanceModeTracker.add(self._na_zmiane_trybu)

    def _na_zmiane_trybu(self, _nowy_tryb: str) -> None:
        if self._ostatni_wykres is not None:
            self._przerysuj_wykres(self._ostatni_wykres)

    def odswiez(self) -> None:
        def zadanie():
            return api_client.pobierz_dashboard()

        def sukces(dane: dict) -> None:
            self._zbuduj_kafelki(dane["kafelki"])
            self._zbuduj_kafelki_ksef(dane["kafelki"])
            self._ostatni_wykres = dane["wykres_przychodow"]
            self._przerysuj_wykres(self._ostatni_wykres)
            self._zbuduj_liste_uwagi(
                dane["faktury_po_terminie"], dane["faktury_odrzucone_ksef"], dane["ponizej_minimum"]
            )

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_kafelki(self, kafelki: dict) -> None:
        for kafelek in self._kafelki:
            kafelek.destroy()
        self._kafelki = []

        liczba_po_terminie = kafelki["liczba_faktur_po_terminie"]

        definicje = [
            (
                "Przychód w tym miesiącu",
                formatowanie.formatuj_kwote(kafelki["przychod_biezacy_miesiac_grosze"]),
                None,
                None,
                lambda: self.on_nawigacja("faktury", status_filtr=None),
            ),
            (
                "Należności",
                formatowanie.formatuj_kwote(kafelki["naleznosci_grosze"]),
                None,
                styl.KOLOR_OSTRZEZENIE if kafelki["naleznosci_grosze"] > 0 else None,
                lambda: self.on_nawigacja("naleznosci", status_filtr=None),
            ),
            (
                "Faktury po terminie",
                str(liczba_po_terminie),
                formatowanie.formatuj_kwote(kafelki["kwota_po_terminie_grosze"])
                if liczba_po_terminie
                else None,
                styl.KOLOR_BLAD if liczba_po_terminie else None,
                lambda: self.on_nawigacja("naleznosci", status_filtr="po_terminie"),
            ),
            (
                "Faktury w tym miesiącu",
                str(kafelki["liczba_faktur_biezacy_miesiac"]),
                None,
                None,
                lambda: self.on_nawigacja("faktury", status_filtr=None),
            ),
        ]

        for indeks, (tytul, wartosc, podtytul, kolor, on_klik) in enumerate(definicje):
            kafelek = _Kafelek(self._ramka_kafelkow, tytul, wartosc, podtytul, kolor, on_klik)
            kafelek.grid(
                row=0,
                column=indeks,
                sticky="nsew",
                padx=(0, styl.ODSTEP_MALY) if indeks < len(definicje) - 1 else 0,
            )
            self._kafelki.append(kafelek)

    def _zbuduj_kafelki_ksef(self, kafelki: dict) -> None:
        for kafelek in self._kafelki_ksef:
            kafelek.destroy()
        self._kafelki_ksef = []

        liczba_oczekujacych = kafelki["liczba_faktur_oczekujacych_ksef"]
        liczba_kosztowych_nowych = kafelki["liczba_dokumentow_kosztowych_nowych"]

        definicje = [
            (
                "Oczekują na wysłanie do KSeF",
                str(liczba_oczekujacych),
                None,
                styl.KOLOR_OSTRZEZENIE if liczba_oczekujacych else None,
                lambda: self.on_nawigacja("faktury", status_filtr=None),
            ),
            (
                "Nowe dokumenty kosztowe",
                str(liczba_kosztowych_nowych),
                None,
                styl.KOLOR_OSTRZEZENIE if liczba_kosztowych_nowych else None,
                lambda: self.on_nawigacja("koszty"),
            ),
        ]

        for indeks, (tytul, wartosc, podtytul, kolor, on_klik) in enumerate(definicje):
            kafelek = _Kafelek(self._ramka_kafelkow_ksef, tytul, wartosc, podtytul, kolor, on_klik)
            kafelek.grid(
                row=0,
                column=indeks,
                sticky="nsew",
                padx=(0, styl.ODSTEP_MALY) if indeks < len(definicje) - 1 else 0,
            )
            self._kafelki_ksef.append(kafelek)

    def _przerysuj_wykres(self, punkty: list[dict]) -> None:
        suma_calkowita = sum(p["suma_brutto_grosze"] for p in punkty)
        if suma_calkowita == 0:
            self._widget_platna.grid_remove()
            self._etykieta_brak_wykresu.grid(
                row=1, column=0, padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_SREDNI)
            )
            return

        self._etykieta_brak_wykresu.grid_remove()
        self._widget_platna.grid(
            row=1, column=0, sticky="nsew", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_SREDNI
        )

        kolor_tla = _kolor(styl.KOLOR_KARTA)
        kolor_slupkow = _kolor(styl.KOLOR_AKCENT)
        kolor_tekstu = _kolor(styl.KOLOR_TEKST_DRUGORZEDNY)
        kolor_siatki = _kolor(styl.KOLOR_OBRAMOWANIE)

        self._figura.patch.set_facecolor(kolor_tla)
        self._osie.clear()
        self._osie.set_facecolor(kolor_tla)

        etykiety_x = [_NAZWY_MIESIECY[p["miesiac"] - 1] for p in punkty]
        wartosci_zlote = [p["suma_brutto_grosze"] / 100 for p in punkty]

        self._osie.bar(etykiety_x, wartosci_zlote, color=kolor_slupkow, width=0.6)
        self._osie.set_ylim(bottom=0)
        self._osie.tick_params(colors=kolor_tekstu, labelsize=9, length=0)
        for nazwa_krawedzi in ("top", "right", "left"):
            self._osie.spines[nazwa_krawedzi].set_visible(False)
        self._osie.spines["bottom"].set_color(kolor_siatki)
        self._osie.yaxis.grid(True, color=kolor_siatki, linewidth=0.6, alpha=0.6)
        self._osie.set_axisbelow(True)

        self._figura.tight_layout()
        self._platno.draw()

    def _zbuduj_liste_uwagi(
        self,
        faktury_po_terminie: list[dict],
        faktury_odrzucone_ksef: list[dict],
        ponizej_minimum: list[dict],
    ) -> None:
        for wiersz in self._wiersze_uwagi:
            wiersz.destroy()
        self._wiersze_uwagi = []

        if not faktury_po_terminie and not faktury_odrzucone_ksef and not ponizej_minimum:
            placeholder = ctk.CTkLabel(
                self._ramka_uwagi,
                text="Brak pozycji wymagających uwagi.",
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            )
            placeholder.grid(row=0, column=0, sticky="w", pady=styl.ODSTEP_MALY)
            self._wiersze_uwagi.append(placeholder)
            return

        dzisiaj = date.today()
        wiersz_idx = 0

        for faktura in faktury_po_terminie:
            termin = date.fromisoformat(str(faktura["termin_platnosci"])[:10])
            dni_zaleglosci = (dzisiaj - termin).days
            lewy = (
                f"{faktura['numer']} — termin {formatowanie.formatuj_date(termin)} "
                f"({dni_zaleglosci} dni temu)"
            )
            prawy = formatowanie.formatuj_kwote(
                faktura["kwota_pozostala_grosze"], faktura["waluta"]
            )
            wiersz = _WierszUwagi(
                self._ramka_uwagi,
                lewy,
                prawy,
                styl.KOLOR_BLAD,
                on_klik=lambda fid=faktura["id"]: self._otworz_fakture(fid),
            )
            wiersz.grid(row=wiersz_idx, column=0, sticky="ew", pady=(0, styl.ODSTEP_MALY))
            self._wiersze_uwagi.append(wiersz)
            wiersz_idx += 1

        for faktura in faktury_odrzucone_ksef:
            lewy = f"{faktura['numer']} — odrzucona przez KSeF"
            prawy = "Wymaga poprawy"
            wiersz = _WierszUwagi(
                self._ramka_uwagi,
                lewy,
                prawy,
                styl.KOLOR_BLAD,
                on_klik=lambda fid=faktura["id"]: self._otworz_fakture(fid),
            )
            wiersz.grid(row=wiersz_idx, column=0, sticky="ew", pady=(0, styl.ODSTEP_MALY))
            self._wiersze_uwagi.append(wiersz)
            wiersz_idx += 1

        for produkt in ponizej_minimum:
            lewy = f"{produkt['produkt_nazwa']} — {produkt['magazyn_nazwa']}"
            prawy = (
                f"{formatowanie.formatuj_ilosc(produkt['ilosc'], produkt['jednostka_miary'])} "
                f"(min. "
                f"{formatowanie.formatuj_ilosc(produkt['stan_minimalny'], produkt['jednostka_miary'])})"
            )
            wiersz = _WierszUwagi(
                self._ramka_uwagi,
                lewy,
                prawy,
                styl.KOLOR_OSTRZEZENIE,
                on_klik=lambda pid=produkt["produkt_id"]: self._otworz_produkt(pid),
            )
            wiersz.grid(row=wiersz_idx, column=0, sticky="ew", pady=(0, styl.ODSTEP_MALY))
            self._wiersze_uwagi.append(wiersz)
            wiersz_idx += 1

    def _otworz_fakture(self, faktura_id: int) -> None:
        SzczegolyFaktury(self, faktura_id=faktura_id, on_zmiana=self.odswiez)

    def _otworz_produkt(self, produkt_id: int) -> None:
        SzczegolyProduktu(self, produkt_id=produkt_id)
