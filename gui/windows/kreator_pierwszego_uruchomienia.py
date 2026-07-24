"""Kreator pierwszego uruchomienia (Faza 18D) - zastepuje wszystkie reczne
kroki, ktore dotychczas wykonywal deweloper przez terminal (reczny wpis
testowej Firmy, reczne ustawienie hasla) czyms, co realny uzytkownik koncowy
moze sam przejsc: dane firmy -> haslo -> opcjonalne ustawienia startowe.

Uruchamiane z gui/main.py PO starcie backendu (prywatny Postgres + serwer
FastAPI), bo Krok 1 (dane firmy) potrzebuje dzialajacego API. Lista krokow
jest budowana DYNAMICZNIE wedlug tego, czego jeszcze brakuje (brak Firmy /
brak hasla) - dzieki temu kreator jest wznawialny: jesli appka zamknie sie
(albo uzytkownik przerwie) miedzy krokami, kolejne uruchomienie zaczyna od
pierwszego wciaz brakujacego kroku, nie od poczatku.
"""

from pathlib import Path

import customtkinter as ctk

from gui import api_client, auth, formatowanie, styl
from gui.api_client import ApiError
from gui.ikona_okna import ustaw_ikone
from gui.integracje_gui import pobierz_z_gus
from gui.logo import wybierz_i_skopiuj_logo
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import (
    Banner,
    formatuj_srodowisko_ksef,
    podepnij_limit_cyfr,
    podepnij_maske_kodu_pocztowego,
    potwierdz,
    przewin_na_gore,
    ustaw_tekst_ladowania,
)

# Podpowiedzi formatu (Faza 27) - patrz gui/windows/formularz_klienta.py, ten
# sam powod (backend ma wlasna walidacje formatu tych dwoch pol).
_PLACEHOLDERY_FIRMY = {
    "kod_pocztowy": "np. 00-950",
    "telefon": "np. +48 123 456 789",
    "bank_numer_konta": "np. PL61 1090 1014 0000 0712 1981 2874",
    "bank_numer_konta_vat": "np. PL61 1090 1014 0000 0712 1981 2874",
}

POLA_FIRMY_KREATORA = [
    ("nazwa", "Nazwa firmy *"),
    ("nip", "NIP *"),
    ("ulica", "Ulica"),
    ("kod_pocztowy", "Kod pocztowy"),
    ("miejscowosc", "Miejscowość"),
    ("kraj", "Kraj"),
    ("email", "Email"),
    ("telefon", "Telefon"),
    ("bank_nazwa", "Nazwa banku"),
    ("bank_numer_konta", "Numer konta bankowego"),
    ("bank_numer_konta_vat", "Numer rachunku VAT (do MPP)"),
]

_ETYKIETY_STAWEK_VAT = [
    formatowanie.ETYKIETY_STAWEK_VAT[s] for s in formatowanie.KOLEJNOSC_STAWEK_VAT
]
_KLUCZE_WG_ETYKIETY_STAWKI = {
    formatowanie.ETYKIETY_STAWEK_VAT[s]: s for s in formatowanie.KOLEJNOSC_STAWEK_VAT
}


def uruchom_kreator_jesli_potrzebny() -> bool:
    """Zwraca True, jesli mozna kontynuowac do glownego okna appki (kreator nie
    byl potrzebny albo zostal ukonczony) - False, jesli uzytkownik przerwal
    (appka powinna sie wtedy zakonczyc)."""
    firma = _pobierz_firme_lub_none()
    haslo_ustawione = auth.czy_haslo_ustawione()

    if firma is not None and haslo_ustawione:
        return True

    okno = _Kreator(firma_istnieje=firma is not None, haslo_ustawione=haslo_ustawione)
    okno.mainloop()
    return okno.ukonczono


def _pobierz_firme_lub_none() -> dict | None:
    try:
        return api_client.pobierz_firme()
    except ApiError as e:
        if e.status_code == 404:
            return None
        raise


class _KrokBazowy(ctk.CTkFrame):
    tytul: str = ""
    podtytul: str = ""
    pomijalny: bool = False

    def __init__(self, master, kreator: "_Kreator"):
        super().__init__(master, fg_color="transparent")
        self.kreator = kreator

    def aktywowano(self) -> None:
        """Wolane za kazdym razem, gdy krok staje sie widoczny."""

    def dalej(self) -> None:
        """Wolane po kliknieciu glownego przycisku (Dalej/Zakoncz) - krok sam
        decyduje, kiedy wywolac self.kreator.przejdz_dalej() (zwykle po
        walidacji i zapisie w tle)."""
        self.kreator.przejdz_dalej()

    def _etykieta_pola(self, master, tekst: str) -> ctk.CTkLabel:
        etykieta = ctk.CTkLabel(
            master,
            text=tekst,
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        etykieta.pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))
        return etykieta


class KrokFirma(_KrokBazowy):
    tytul = "Dane Twojej firmy"
    podtytul = (
        "Te dane pojawią się na każdej wystawionej fakturze. "
        "Możesz je później zmienić w Ustawieniach."
    )

    def __init__(self, master, kreator):
        super().__init__(master, kreator)

        self._pola: dict[str, ctk.CTkEntry] = {}
        self._firma_zapisana = False
        self._logo_sciezka: str | None = None
        pierwsze_pole = None

        self._banner = Banner(self)

        for klucz, etykieta_tekst in POLA_FIRMY_KREATORA:
            etykieta = self._etykieta_pola(self, etykieta_tekst)
            if pierwsze_pole is None:
                pierwsze_pole = etykieta

            if klucz == "nip":
                wiersz = ctk.CTkFrame(self, fg_color="transparent")
                wiersz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
                wiersz.grid_columnconfigure(0, weight=1)
                pole = ctk.CTkEntry(wiersz, font=styl.CZCIONKA_TRESC)
                pole.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
                podepnij_limit_cyfr(pole, 10)
                self._przycisk_gus = ctk.CTkButton(
                    wiersz,
                    text="Pobierz z GUS",
                    font=styl.CZCIONKA_DROBNA,
                    width=110,
                    fg_color="transparent",
                    border_width=1,
                    border_color=styl.KOLOR_OBRAMOWANIE,
                    text_color=styl.KOLOR_TEKST_GLOWNY,
                    hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                    command=self._pobierz_z_gus,
                )
                self._przycisk_gus.grid(row=0, column=1)
            else:
                pole = ctk.CTkEntry(
                    self, font=styl.CZCIONKA_TRESC,
                    placeholder_text=_PLACEHOLDERY_FIRMY.get(klucz, ""),
                )
                pole.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
                if klucz == "kraj":
                    pole.insert(0, "Polska")
                if klucz == "kod_pocztowy":
                    podepnij_maske_kodu_pocztowego(pole)
            self._pola[klucz] = pole

        self._banner.ustaw_geometrie(
            lambda: self._banner.pack(fill="x", pady=(0, styl.ODSTEP_MALY), before=pierwsze_pole)
        )

        ctk.CTkFrame(self, fg_color=styl.KOLOR_OBRAMOWANIE, height=1).pack(
            fill="x", pady=styl.ODSTEP_SREDNI
        )
        self._etykieta_pola(self, "Logo firmy (opcjonalnie)")
        wiersz_logo = ctk.CTkFrame(self, fg_color="transparent")
        wiersz_logo.pack(fill="x")
        wiersz_logo.grid_columnconfigure(0, weight=1)
        self._etykieta_logo = ctk.CTkLabel(
            wiersz_logo,
            text="Nie wybrano",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        self._etykieta_logo.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        ctk.CTkButton(
            wiersz_logo,
            text="Wybierz plik...",
            font=styl.CZCIONKA_DROBNA,
            width=110,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._wybierz_logo,
        ).grid(row=0, column=1)

    def aktywowano(self) -> None:
        self._pola["nazwa"].focus_set()

    def _wybierz_logo(self) -> None:
        sciezka = wybierz_i_skopiuj_logo(self.kreator)
        if sciezka:
            self._logo_sciezka = sciezka
            self._etykieta_logo.configure(
                text=Path(sciezka).name, text_color=styl.KOLOR_TEKST_GLOWNY
            )

    def _pobierz_z_gus(self) -> None:
        def wypelnij(podmiot: dict) -> None:
            mapowanie = {
                "nazwa": "nazwa",
                "ulica": "ulica",
                "kod_pocztowy": "kod_pocztowy",
                "miejscowosc": "miejscowosc",
            }
            for klucz_podmiotu, klucz_pola in mapowanie.items():
                wartosc = podmiot.get(klucz_podmiotu)
                if wartosc:
                    self._pola[klucz_pola].delete(0, "end")
                    self._pola[klucz_pola].insert(0, wartosc)

        pobierz_z_gus(
            self.kreator, self._pola["nip"].get(), self._przycisk_gus, self._banner, wypelnij
        )

    def dalej(self) -> None:
        nazwa = self._pola["nazwa"].get().strip()
        nip = self._pola["nip"].get().strip()
        if not nazwa or not nip:
            self._banner.pokaz("Nazwa i NIP firmy są wymagane.")
            return
        self._banner.ukryj()

        dane: dict = {"nazwa": nazwa, "nip": nip}
        for klucz in (
            "ulica", "kod_pocztowy", "miejscowosc", "kraj", "email", "telefon",
            "bank_nazwa", "bank_numer_konta", "bank_numer_konta_vat",
        ):
            wartosc = self._pola[klucz].get().strip()
            if wartosc:
                dane[klucz] = wartosc
        if self._logo_sciezka:
            dane["logo_path"] = self._logo_sciezka

        self.kreator.ustaw_przycisk_dalej_zajety(True, "Dalej")

        def zadanie():
            if self._firma_zapisana:
                return api_client.aktualizuj_firme(dane)
            return api_client.utworz_firme(dane)

        def sukces(_wynik) -> None:
            self._firma_zapisana = True
            self.kreator.ustaw_przycisk_dalej_zajety(False, "Dalej")
            self.kreator.przejdz_dalej()

        def blad(e: ApiError) -> None:
            self.kreator.ustaw_przycisk_dalej_zajety(False, "Dalej")
            self._banner.pokaz(e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)


class KrokHaslo(_KrokBazowy):
    tytul = "Ustaw hasło"
    podtytul = (
        "Będziesz go używać przy każdym uruchomieniu aplikacji, żeby nikt inny "
        "przy tym komputerze nie miał dostępu do Twoich faktur."
    )

    def __init__(self, master, kreator):
        super().__init__(master, kreator)
        self._haslo_zapisane = False

        self._banner = Banner(self)
        self._banner.ustaw_geometrie(lambda: self._banner.pack(fill="x", pady=(0, styl.ODSTEP_MALY)))

        self._etykieta_pola(self, "Nowe hasło")
        self._pole_haslo = ctk.CTkEntry(self, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_haslo.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(self, "Powtórz hasło")
        self._pole_powtorz = ctk.CTkEntry(self, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_powtorz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._pole_haslo.bind("<Return>", lambda _z: self._pole_powtorz.focus_set())
        self._pole_powtorz.bind("<Return>", lambda _z: self.dalej())

    def aktywowano(self) -> None:
        self._pole_haslo.focus_set()

    def dalej(self) -> None:
        if self._haslo_zapisane:
            self.kreator.przejdz_dalej()
            return

        haslo = self._pole_haslo.get()
        powtorz = self._pole_powtorz.get()
        if len(haslo) < 4:
            self._banner.pokaz("Hasło musi mieć co najmniej 4 znaki.")
            return
        if haslo != powtorz:
            self._banner.pokaz("Hasła nie są identyczne.")
            return
        self._banner.ukryj()

        self.kreator.ustaw_przycisk_dalej_zajety(True, "Dalej")

        def zadanie():
            auth.ustaw_haslo(haslo)

        def sukces(_wynik) -> None:
            self._haslo_zapisane = True
            self.kreator.ustaw_przycisk_dalej_zajety(False, "Dalej")
            self.kreator.przejdz_dalej()

        def blad(e: ApiError) -> None:
            self.kreator.ustaw_przycisk_dalej_zajety(False, "Dalej")
            self._banner.pokaz(e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)


class KrokUstawienia(_KrokBazowy):
    tytul = "Ostatnie ustawienia"
    podtytul = "Możesz to skonfigurować teraz albo później w Ustawieniach."
    pomijalny = True

    def __init__(self, master, kreator):
        super().__init__(master, kreator)

        self._etykieta_pola(self, "Domyślna stawka VAT na fakturach")
        self._var_vat = ctk.StringVar(value=formatowanie.ETYKIETY_STAWEK_VAT["23"])
        ctk.CTkOptionMenu(
            self,
            values=_ETYKIETY_STAWEK_VAT,
            variable=self._var_vat,
            font=styl.CZCIONKA_TRESC,
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkFrame(self, fg_color=styl.KOLOR_OBRAMOWANIE, height=1).pack(
            fill="x", pady=(0, styl.ODSTEP_SREDNI)
        )
        ctk.CTkLabel(
            self, text="Numeracja faktur", font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        ctk.CTkLabel(
            self,
            text=(
                "Faktury będą numerowane automatycznie w formacie FV/RRRR/NNNN "
                "(np. FV/2026/0001)."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=480,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkFrame(self, fg_color=styl.KOLOR_OBRAMOWANIE, height=1).pack(
            fill="x", pady=(0, styl.ODSTEP_SREDNI)
        )
        ctk.CTkLabel(
            self, text="Środowisko KSeF", font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        ctk.CTkLabel(
            self,
            text=(
                "KSeF to rządowy system e-Faktur. Środowisko TESTOWE służy do "
                "ćwiczeń — nic, co tu zrobisz, nie trafia naprawdę do urzędu "
                "skarbowego. Środowisko PRODUKCYJNE wysyła prawdziwe faktury. "
                "Zostań na TESTOWYM, dopóki nie będziesz gotowy/-a wysyłać "
                "prawdziwych faktur przez KSeF."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=480,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._banda_ksef = ctk.CTkLabel(
            self, text="", font=styl.CZCIONKA_TRESC_POGRUBIONA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self._banda_ksef.pack(fill="x", pady=(0, styl.ODSTEP_MALY), ipady=styl.ODSTEP_MALY)

        self._var_srodowisko = ctk.StringVar(value="Testowe")
        ctk.CTkSegmentedButton(
            self,
            values=["Testowe", "Produkcyjne"],
            variable=self._var_srodowisko,
            font=styl.CZCIONKA_TRESC,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._na_zmiane_srodowiska,
        ).pack(fill="x")

        self._banner = Banner(self)
        self._banner.ustaw_geometrie(lambda: self._banner.pack(fill="x", pady=(styl.ODSTEP_MALY, 0)))

        self._odswiez_banda("testowe")

    def _odswiez_banda(self, srodowisko: str) -> None:
        tekst, kolor_tekstu, kolor_tla = formatuj_srodowisko_ksef(srodowisko)
        self._banda_ksef.configure(text=tekst, fg_color=kolor_tla, text_color=kolor_tekstu)

    def _na_zmiane_srodowiska(self, wartosc: str) -> None:
        if wartosc == "Produkcyjne":
            potwierdzono = potwierdz(
                self.kreator,
                "Zamierzasz przełączyć integrację KSeF na ŚRODOWISKO PRODUKCYJNE.\n\n"
                "Od tego momentu żądania będą wysyłane do prawdziwego systemu "
                "Ministerstwa Finansów, z rzeczywistymi konsekwencjami prawnymi i "
                "finansowymi.\n\n"
                "Czy na pewno chcesz kontynuować?",
                tytul="Przełączenie na środowisko produkcyjne KSeF",
                tekst_tak="Przełącz na produkcję",
                niebezpieczne=True,
            )
            if not potwierdzono:
                self._var_srodowisko.set("Testowe")
                wartosc = "Testowe"
        self._odswiez_banda("produkcyjne" if wartosc == "Produkcyjne" else "testowe")

    def dalej(self) -> None:
        stawka_vat = _KLUCZE_WG_ETYKIETY_STAWKI[self._var_vat.get()]
        srodowisko = "produkcyjne" if self._var_srodowisko.get() == "Produkcyjne" else "testowe"

        self.kreator.ustaw_przycisk_dalej_zajety(True, "Zakończ")

        def zadanie():
            api_client.aktualizuj_firme({"domyslna_stawka_vat": stawka_vat})
            return api_client.zapisz_ustawienia_ksef({"srodowisko": srodowisko})

        def sukces(_wynik) -> None:
            self.kreator.ustaw_przycisk_dalej_zajety(False, "Zakończ")
            self.kreator.przejdz_dalej()

        def blad(e: ApiError) -> None:
            self.kreator.ustaw_przycisk_dalej_zajety(False, "Zakończ")
            self._banner.pokaz(e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)


class _Kreator(ctk.CTk):
    """Powloka kreatora - naglowek z numerem kroku, przewijalna tresc kroku
    aktywnego, stopka z nawigacja Wstecz/Pomin/Dalej. Instancje krokow sa
    tworzone LENIWIE i trzymane w pamieci (nie niszczone przy zmianie kroku),
    zeby cofniecie sie (Wstecz) nie gubilo ani wpisanych wartosci, ani flagi
    'juz zapisane' (patrz KrokFirma._firma_zapisana) - bez tego powtorne
    klikniecie Dalej po powrocie proboowaloby ponownie utworzyc Firme i
    dostawaloby blad 400 'juz skonfigurowane'."""

    def __init__(self, firma_istnieje: bool, haslo_ustawione: bool):
        super().__init__()
        ustaw_ikone(self)
        self.ukonczono = False

        self.title("Faktury Pro — pierwsze uruchomienie")
        self.geometry("560x640")
        self.resizable(False, False)
        self.configure(fg_color=styl.KOLOR_TLO)
        self.protocol("WM_DELETE_WINDOW", self._na_zamkniecie)

        self._klasy_krokow: list[type[_KrokBazowy]] = []
        if not firma_istnieje:
            self._klasy_krokow.append(KrokFirma)
        if not haslo_ustawione:
            self._klasy_krokow.append(KrokHaslo)
        self._klasy_krokow.append(KrokUstawienia)

        self._instancje_krokow: dict[int, _KrokBazowy] = {}
        self._indeks = 0
        self._krok_aktywny: _KrokBazowy | None = None

        naglowek = ctk.CTkFrame(self, fg_color="transparent")
        naglowek.pack(fill="x", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_MALY))

        self._etykieta_krok = ctk.CTkLabel(
            naglowek, text="", font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_krok.pack(fill="x")

        self._etykieta_tytul = ctk.CTkLabel(
            naglowek, text="", font=styl.NAGLOWEK_1, text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        )
        self._etykieta_tytul.pack(fill="x", pady=(styl.ODSTEP_MIKRO, 0))

        self._etykieta_podtytul = ctk.CTkLabel(
            naglowek, text="", font=styl.CZCIONKA_TRESC, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w", wraplength=500, justify="left",
        )
        self._etykieta_podtytul.pack(fill="x", pady=(styl.ODSTEP_MIKRO, 0))

        self._kontener_tresci = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._kontener_tresci.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_MALY)

        stopka = ctk.CTkFrame(self, fg_color="transparent")
        stopka.pack(fill="x", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_MALY, styl.ODSTEP_DUZY))
        stopka.grid_columnconfigure(1, weight=1)

        self._przycisk_wstecz = ctk.CTkButton(
            stopka, text="Wstecz", width=100, fg_color="transparent", border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE, text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY, command=self._wstecz,
        )
        self._przycisk_wstecz.grid(row=0, column=0)

        self._przycisk_pomin = ctk.CTkButton(
            stopka, text="Pomiń", width=90, fg_color="transparent", border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE, text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY, command=self._pomin,
        )

        self._przycisk_dalej = ctk.CTkButton(
            stopka, text="Dalej", width=120, fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER, command=self._dalej,
        )
        self._przycisk_dalej.grid(row=0, column=3)

        self._pokaz_krok(0)

    def _pokaz_krok(self, indeks: int) -> None:
        if self._krok_aktywny is not None:
            self._krok_aktywny.pack_forget()

        self._indeks = indeks
        if indeks not in self._instancje_krokow:
            klasa = self._klasy_krokow[indeks]
            self._instancje_krokow[indeks] = klasa(self._kontener_tresci, self)
        self._krok_aktywny = self._instancje_krokow[indeks]
        self._krok_aktywny.pack(fill="both", expand=True)
        # Bez tego: jesli poprzedni krok byl dluzszy i uzytkownik go przewinal
        # w dol (np. wypelniajac opcjonalne pola adresu/banku w Kroku 1), nowy,
        # krotszy krok (np. haslo w Kroku 2) renderuje sie poprawnie, ale
        # POZA widocznym obszarem - customtkinter nie resetuje przewiniecia
        # sam. Zweryfikowane jako realna przyczyna zgloszenia "pole hasla
        # czasem sie nie pojawia".
        przewin_na_gore(self._kontener_tresci)

        self._etykieta_krok.configure(text=f"Krok {indeks + 1} z {len(self._klasy_krokow)}")
        self._etykieta_tytul.configure(text=self._krok_aktywny.tytul)
        self._etykieta_podtytul.configure(text=self._krok_aktywny.podtytul)

        if indeks == 0:
            self._przycisk_wstecz.grid_remove()
        else:
            self._przycisk_wstecz.grid(row=0, column=0)

        ostatni = indeks == len(self._klasy_krokow) - 1
        self._przycisk_dalej.configure(text="Zakończ" if ostatni else "Dalej")
        if ostatni and self._krok_aktywny.pomijalny:
            self._przycisk_pomin.grid(row=0, column=2, padx=(0, styl.ODSTEP_MALY))
        else:
            self._przycisk_pomin.grid_remove()

        self._krok_aktywny.aktywowano()

    def _wstecz(self) -> None:
        if self._indeks > 0:
            self._pokaz_krok(self._indeks - 1)

    def _dalej(self) -> None:
        if self._krok_aktywny is not None:
            self._krok_aktywny.dalej()

    def _pomin(self) -> None:
        if self._krok_aktywny is not None and self._krok_aktywny.pomijalny:
            self.przejdz_dalej()

    def przejdz_dalej(self) -> None:
        if self._indeks + 1 < len(self._klasy_krokow):
            self._pokaz_krok(self._indeks + 1)
        else:
            self.ukonczono = True
            self.destroy()

    def ustaw_przycisk_dalej_zajety(self, zajety: bool, tekst_zwykly: str) -> None:
        ustaw_tekst_ladowania(self._przycisk_dalej, zajety, tekst_zwykly, "Zapisywanie...")

    def _na_zamkniecie(self) -> None:
        potwierdzono = potwierdz(
            self,
            "Na pewno przerwać konfigurację?\n\n"
            "Będziesz mógł/mogła dokończyć przy następnym uruchomieniu aplikacji — "
            "nic, co już zapisano, nie zostanie utracone.",
            tytul="Przerwać konfigurację?",
            tekst_tak="Przerwij",
        )
        if potwierdzono:
            self.ukonczono = False
            self.destroy()
