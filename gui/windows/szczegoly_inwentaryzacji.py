from decimal import Decimal
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import (
    Banner,
    komunikat_bledu,
    komunikat_ostrzezenie,
    pokaz_toast,
    ustaw_tekst_ladowania,
)
from gui.windows.baza_formularza import OknoFormularza


class _WierszLiczenia(ctk.CTkFrame):
    def __init__(self, master, pozycja: dict, edytowalny: bool):
        super().__init__(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self.produkt_id = pozycja["produkt_id"]
        self.produkt_nazwa = pozycja["produkt_nazwa"]
        self.jednostka = pozycja["jednostka_miary"]
        self.stan_systemowy = Decimal(str(pozycja["stan_systemowy"]))

        for kolumna, waga in enumerate([3, 2, 2]):
            self.grid_columnconfigure(kolumna, weight=waga)

        ctk.CTkLabel(
            self,
            text=pozycja["produkt_nazwa"],
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(styl.ODSTEP_MALY, styl.ODSTEP_MIKRO), pady=styl.ODSTEP_MALY)

        ctk.CTkLabel(
            self,
            text=formatowanie.formatuj_ilosc(self.stan_systemowy, self.jednostka),
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=styl.ODSTEP_MIKRO, pady=styl.ODSTEP_MALY)

        if edytowalny:
            self.pole_faktyczny = ctk.CTkEntry(
                self, placeholder_text="Stan faktyczny", font=styl.CZCIONKA_TRESC
            )
            if pozycja["stan_faktyczny"] is not None:
                self.pole_faktyczny.insert(
                    0,
                    formatowanie.formatuj_ilosc(Decimal(str(pozycja["stan_faktyczny"]))),
                )
            self.pole_faktyczny.grid(
                row=0, column=2, sticky="ew", padx=(styl.ODSTEP_MIKRO, styl.ODSTEP_MALY), pady=styl.ODSTEP_MALY
            )
        else:
            self.pole_faktyczny = None
            wartosc = pozycja["stan_faktyczny"]
            tekst = (
                formatowanie.formatuj_ilosc(Decimal(str(wartosc)), self.jednostka)
                if wartosc is not None
                else "— (nie policzono)"
            )
            ctk.CTkLabel(
                self,
                text=tekst,
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
            ).grid(row=0, column=2, sticky="ew", padx=(styl.ODSTEP_MIKRO, styl.ODSTEP_MALY), pady=styl.ODSTEP_MALY)

    def pobierz_wpis(self) -> dict | None:
        """Zwraca {'produkt_id', 'stan_faktyczny'} jesli pole ma tresc, inaczej
        None (produkt jeszcze nie policzony w tej sesji). Rzuca ValueError przy
        nieprawidlowej tresci pola."""
        if self.pole_faktyczny is None:
            return None
        tekst = self.pole_faktyczny.get().strip()
        if not tekst:
            return None
        wartosc = formatowanie.parsuj_liczbe_dodatnia(
            tekst, "stan faktyczny", wymagaj_dodatniej=False
        )
        return {"produkt_id": self.produkt_id, "stan_faktyczny": str(wartosc)}


class SzczegolyInwentaryzacji(OknoFormularza):
    def __init__(
        self,
        master,
        inwentaryzacja_id: int,
        on_zmiana: Callable[[], None] | None = None,
    ):
        super().__init__(master)
        self.title("Spis inwentaryzacyjny")
        self.geometry("760x680")

        self._inwentaryzacja_id = inwentaryzacja_id
        self._on_zmiana = on_zmiana or (lambda: None)
        self._wiersze: list[_WierszLiczenia] = []

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        self._zaladuj()

    def _zaladuj(self) -> None:
        def zadanie():
            inwentaryzacja = api_client.pobierz_inwentaryzacje_szczegoly(
                self._inwentaryzacja_id
            )
            magazyny = api_client.pobierz_magazyny(tylko_aktywne=False, limit=200)
            return inwentaryzacja, magazyny

        def sukces(wynik) -> None:
            inwentaryzacja, magazyny = wynik
            magazyny_wg_id = {m["id"]: m["nazwa"] for m in magazyny}
            self._etykieta_ladowania.destroy()
            self._zbuduj_widok(inwentaryzacja, magazyny_wg_id)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            self.destroy()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_widok(self, inwentaryzacja: dict, magazyny_wg_id: dict[int, str]) -> None:
        edytowalny = inwentaryzacja["status"] == "w_trakcie"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._banner = Banner(self)
        self._banner.ustaw_geometrie(
            lambda: self._banner.grid(
                row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0)
            )
        )

        naglowek = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        naglowek.grid(
            row=1, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        ctk.CTkLabel(
            naglowek,
            text=f"Spis {inwentaryzacja['numer']}",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(anchor="w", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY))

        wiersze_info = [
            (
                "Magazyn",
                magazyny_wg_id.get(inwentaryzacja["magazyn_id"], f"#{inwentaryzacja['magazyn_id']}"),
                None,
            ),
            (
                "Status",
                formatowanie.formatuj_status_inwentaryzacji(inwentaryzacja["status"]),
                formatowanie.kolor_statusu_inwentaryzacji(inwentaryzacja["status"]),
            ),
            (
                "Data rozpoczęcia",
                formatowanie.formatuj_date(inwentaryzacja["data_rozpoczecia"]),
                None,
            ),
        ]
        if inwentaryzacja.get("data_zakonczenia"):
            wiersze_info.append(
                ("Data zakończenia", formatowanie.formatuj_date(inwentaryzacja["data_zakonczenia"]), None)
            )

        for etykieta, wartosc, kolor in wiersze_info:
            wiersz = ctk.CTkFrame(naglowek, fg_color="transparent")
            wiersz.pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=2)
            ctk.CTkLabel(
                wiersz,
                text=f"{etykieta}:",
                font=styl.CZCIONKA_ETYKIETA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                width=160,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                wiersz,
                text=wartosc,
                font=styl.CZCIONKA_TRESC_POGRUBIONA if kolor else styl.CZCIONKA_TRESC,
                text_color=kolor or styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
            ).pack(side="left")
        ctk.CTkFrame(naglowek, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        pasek_kolumn = ctk.CTkFrame(self, fg_color="transparent")
        pasek_kolumn.grid(row=2, column=0, sticky="ew", padx=styl.ODSTEP_DUZY)
        for kolumna, (waga, etykieta) in enumerate(
            [(3, "Produkt"), (2, "Stan systemowy"), (2, "Stan faktyczny")]
        ):
            pasek_kolumn.grid_columnconfigure(kolumna, weight=waga)
            ctk.CTkLabel(
                pasek_kolumn,
                text=etykieta,
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                anchor="w",
            ).grid(row=0, column=kolumna, sticky="ew", padx=(styl.ODSTEP_MALY if kolumna == 0 else 4))

        kontener_wierszy = ctk.CTkScrollableFrame(self, fg_color=styl.KOLOR_TLO)
        kontener_wierszy.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_MALY, styl.ODSTEP_MALY),
        )

        if not inwentaryzacja["pozycje"]:
            ctk.CTkLabel(
                kontener_wierszy,
                text="Brak towarów magazynowych do policzenia.",
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            ).pack(pady=styl.ODSTEP_DUZY)

        for pozycja in inwentaryzacja["pozycje"]:
            wiersz = _WierszLiczenia(kontener_wierszy, pozycja, edytowalny)
            wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
            self._wiersze.append(wiersz)

        if edytowalny:
            pasek_akcji = ctk.CTkFrame(self, fg_color="transparent")
            pasek_akcji.grid(
                row=4, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY)
            )
            self._przycisk_zapisz = ctk.CTkButton(
                pasek_akcji,
                text="Zapisz postęp",
                font=styl.CZCIONKA_TRESC,
                fg_color="transparent",
                border_width=1,
                border_color=styl.KOLOR_OBRAMOWANIE,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                command=self._zapisz_postep,
            )
            self._przycisk_zapisz.pack(side="left", padx=(0, styl.ODSTEP_MALY))
            self._przycisk_zamknij = ctk.CTkButton(
                pasek_akcji,
                text="Zamknij spis",
                font=styl.CZCIONKA_TRESC,
                fg_color=styl.KOLOR_AKCENT,
                hover_color=styl.KOLOR_AKCENT_HOVER,
                command=self._zamknij_spis,
            )
            self._przycisk_zamknij.pack(side="left")
            self.ustaw_akcje_zapisu(self._zapisz_postep, self._przycisk_zapisz)

        self.zapamietaj_stan_poczatkowy()

    def _ustaw_przyciski_aktywne(self, aktywne: bool) -> None:
        ustaw_tekst_ladowania(self._przycisk_zapisz, not aktywne, "Zapisz postęp")
        stan = "normal" if aktywne else "disabled"
        self._przycisk_zamknij.configure(state=stan)

    def _zbierz_wpisy(self) -> list[dict] | None:
        wpisy: list[dict] = []
        for wiersz in self._wiersze:
            try:
                wpis = wiersz.pobierz_wpis()
            except ValueError as e:
                self._banner.pokaz(f"{wiersz.produkt_nazwa}: {e}")
                return None
            if wpis is not None:
                wpisy.append(wpis)
        self._banner.ukryj()
        return wpisy

    def _odswiez_w_miejscu(self) -> None:
        inwentaryzacja_id = self._inwentaryzacja_id
        on_zmiana = self._on_zmiana
        master = self.master
        self.destroy()
        SzczegolyInwentaryzacji(master, inwentaryzacja_id=inwentaryzacja_id, on_zmiana=on_zmiana)

    def _zapisz_postep(self) -> None:
        wpisy = self._zbierz_wpisy()
        if wpisy is None:
            return
        if not wpisy:
            self._banner.pokaz("Wpisz stan faktyczny co najmniej jednego produktu.")
            return

        self._ustaw_przyciski_aktywne(False)

        def zadanie():
            return api_client.zapisz_pozycje_inwentaryzacji(self._inwentaryzacja_id, wpisy)

        def sukces(_wynik) -> None:
            self._on_zmiana()
            master = self.master
            self._odswiez_w_miejscu()
            pokaz_toast(master, "Postęp spisu zapisany.")

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zamknij_spis(self) -> None:
        wpisy = self._zbierz_wpisy()
        if wpisy is None:
            return

        wpisy_wg_produktu = {w["produkt_id"]: Decimal(w["stan_faktyczny"]) for w in wpisy}
        liczba_pw = 0
        liczba_rw = 0
        for wiersz in self._wiersze:
            if wiersz.produkt_id not in wpisy_wg_produktu:
                continue
            roznica = wpisy_wg_produktu[wiersz.produkt_id] - wiersz.stan_systemowy
            if roznica > 0:
                liczba_pw += 1
            elif roznica < 0:
                liczba_rw += 1

        if liczba_pw == 0 and liczba_rw == 0:
            tresc = (
                "Wszystkie policzone stany zgadzają się z systemowymi - żaden "
                "dokument korygujący nie zostanie utworzony."
            )
        else:
            czesci = []
            if liczba_pw:
                czesci.append(f"1 dokument PW z {liczba_pw} pozycją/-ami (nadwyżki)")
            if liczba_rw:
                czesci.append(f"1 dokument RW z {liczba_rw} pozycją/-ami (niedobory)")
            tresc = "Zostanie wygenerowany: " + " oraz ".join(czesci) + "."

        nieliczone = sum(
            1
            for wiersz in self._wiersze
            if wiersz.pole_faktyczny is not None and wiersz.produkt_id not in wpisy_wg_produktu
        )
        if nieliczone:
            tresc += (
                f"\n\n{nieliczone} produkt(y) bez wpisanego stanu faktycznego "
                "zostaną pominięte (bez korekty)."
            )

        if not messagebox.askyesno(
            "Zamknąć spis?",
            f"{tresc}\n\nPo zamknięciu spis nie będzie już edytowalny. Kontynuować?",
            parent=self,
        ):
            return

        self._ustaw_przyciski_aktywne(False)

        def zadanie():
            if wpisy:
                api_client.zapisz_pozycje_inwentaryzacji(self._inwentaryzacja_id, wpisy)
            return api_client.zamknij_inwentaryzacje(self._inwentaryzacja_id)

        def sukces(wynik: dict) -> None:
            self._on_zmiana()
            ostrzezenia = wynik.get("ostrzezenia") or []
            inwentaryzacja_id = self._inwentaryzacja_id
            on_zmiana = self._on_zmiana
            master = self.master
            self.destroy()
            if ostrzezenia:
                komunikat_ostrzezenie(
                    master, "Spis zamknięty, ale:\n\n" + "\n\n".join(ostrzezenia)
                )
            else:
                pokaz_toast(master, "Spis zamknięty.")
            SzczegolyInwentaryzacji(master, inwentaryzacja_id=inwentaryzacja_id, on_zmiana=on_zmiana)

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
