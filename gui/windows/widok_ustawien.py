import os
import shutil
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app import profil
from app.wersja import WERSJA
from gui import api_client, auth, diagnostyka, formatowanie, nastawienia, profile_rejestr, styl
from gui import kopia_zapasowa as kz
from gui.integracje_gui import pobierz_z_gus
from gui.logo import wybierz_i_skopiuj_logo
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import (
    Banner,
    formatuj_srodowisko_ksef,
    komunikat_bledu,
    komunikat_info,
    pokaz_toast,
    ustaw_tekst_ladowania,
)
from gui.windows.dialog_kopii_zapasowej import DialogPrzywrocBackup, DialogWykonajBackup
from gui.windows.dialog_wyboru_urzedu import DialogWyboruUrzeduSkarbowego

# (klucz, etykieta, wymagane)
POLA_FIRMY = [
    ("nazwa", "Nazwa *", True),
    ("nip", "NIP *", True),
    ("ulica", "Ulica", False),
    ("kod_pocztowy", "Kod pocztowy", False),
    ("miejscowosc", "Miejscowość", False),
    ("kraj", "Kraj", False),
    ("email", "Email", False),
    ("telefon", "Telefon", False),
    ("bank_nazwa", "Nazwa banku", False),
    ("bank_numer_konta", "Numer konta bankowego", False),
    ("bank_numer_konta_vat", "Numer rachunku VAT (do MPP)", False),
]

ETYKIETA_JDG = "Osoba fizyczna (JDG)"
ETYKIETA_SPOLKA = "Spółka / inna osoba niefizyczna"

ETYKIETA_OSTRZEGAJ = "Ostrzegaj"
ETYKIETA_BLOKUJ = "Blokuj"

_ETYKIETY_STAWEK_VAT = [
    formatowanie.ETYKIETY_STAWEK_VAT[s] for s in formatowanie.KOLEJNOSC_STAWEK_VAT
]
_KLUCZE_WG_ETYKIETY_STAWKI_VAT = {
    formatowanie.ETYKIETY_STAWEK_VAT[s]: s for s in formatowanie.KOLEJNOSC_STAWEK_VAT
}


class WidokUstawien(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(row=0, column=0, sticky="nsew")

        wrapper = ctk.CTkFrame(przewijany, fg_color="transparent", width=360)
        wrapper.pack(pady=styl.ODSTEP_DUZY)

        self._zbuduj_karte_wygladu(wrapper)
        self._zbuduj_karte_firmy(wrapper)
        self._zbuduj_karte_backupu(wrapper)
        self._zbuduj_karte_integracji_gus(wrapper)
        self._zbuduj_karte_ksef(wrapper)
        self._zbuduj_karte_email(wrapper)
        self._zbuduj_karte_przypomnien(wrapper)
        self._zbuduj_karte_hasla(wrapper)
        self._zbuduj_karte_o_aplikacji(wrapper)
        self._zbuduj_karte_diagnostyki(wrapper)
        self._zbuduj_karte_usuwania_profilu(wrapper)

    def _zbuduj_karte_wygladu(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Wygląd",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        self._etykieta_pola(wewnatrz, "Tryb kolorystyczny")

        tryb_aktualny = nastawienia.wczytaj_tryb_wygladu()
        self._var_tryb = ctk.StringVar(
            value=nastawienia.ETYKIETY_TRYBOW_WYGLADU[tryb_aktualny]
        )
        self._klucze_wg_etykiety = {
            etykieta: klucz
            for klucz, etykieta in nastawienia.ETYKIETY_TRYBOW_WYGLADU.items()
        }

        ctk.CTkSegmentedButton(
            wewnatrz,
            values=list(nastawienia.ETYKIETY_TRYBOW_WYGLADU.values()),
            variable=self._var_tryb,
            font=styl.CZCIONKA_TRESC,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zmien_tryb_wygladu,
        ).pack(fill="x")

    def _zmien_tryb_wygladu(self, etykieta: str) -> None:
        tryb = self._klucze_wg_etykiety[etykieta]
        nastawienia.zastosuj_tryb_wygladu(tryb)
        nastawienia.zapisz_tryb_wygladu(tryb)

    # -- dane firmy (Faza 14 - wczesniej appka nie mialo gdzie ich wpisac,
    # a sa potrzebne jako kontekst dla przycisku "Pobierz z GUS" i do
    # weryfikacji bialej listy przy fakturze) --------------------------------

    def _zbuduj_karte_firmy(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Dane firmy",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        self._banner_firmy = Banner(wewnatrz)
        self._banner_firmy.ustaw_geometrie(
            lambda: self._banner_firmy.pack(fill="x", pady=(0, styl.ODSTEP_MALY), before=self._pierwsze_pole_firmy)
        )

        self._firma_istnieje = False
        self._pola_firmy: dict[str, ctk.CTkEntry] = {}
        self._pierwsze_pole_firmy = None

        for klucz, etykieta, _wymagane in POLA_FIRMY:
            etykieta_pola = self._etykieta_pola(wewnatrz, etykieta)
            if self._pierwsze_pole_firmy is None:
                self._pierwsze_pole_firmy = etykieta_pola

            if klucz == "nip":
                wiersz_nip = ctk.CTkFrame(wewnatrz, fg_color="transparent")
                wiersz_nip.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
                wiersz_nip.grid_columnconfigure(0, weight=1)
                pole = ctk.CTkEntry(wiersz_nip, font=styl.CZCIONKA_TRESC)
                pole.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
                self._przycisk_gus_firmy = ctk.CTkButton(
                    wiersz_nip,
                    text="Pobierz z GUS",
                    font=styl.CZCIONKA_DROBNA,
                    width=110,
                    fg_color="transparent",
                    border_width=1,
                    border_color=styl.KOLOR_OBRAMOWANIE,
                    text_color=styl.KOLOR_TEKST_GLOWNY,
                    hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                    command=self._pobierz_firme_z_gus,
                )
                self._przycisk_gus_firmy.grid(row=0, column=1)
            else:
                pole = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC)
                pole.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
            self._pola_firmy[klucz] = pole

        # -- logo i domyslna stawka VAT (Faza 18D - najpierw wprowadzane w
        # kreatorze pierwszego uruchomienia, ale musza byc zmienialne tez tu,
        # zeby nie zostawic uzytkownika bez mozliwosci poprawki po fakcie) --
        ctk.CTkFrame(wewnatrz, fg_color=styl.KOLOR_OBRAMOWANIE, height=1).pack(
            fill="x", pady=styl.ODSTEP_SREDNI
        )
        self._etykieta_pola(wewnatrz, "Logo firmy")
        wiersz_logo = ctk.CTkFrame(wewnatrz, fg_color="transparent")
        wiersz_logo.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        wiersz_logo.grid_columnconfigure(0, weight=1)
        self._logo_sciezka: str | None = None
        self._etykieta_logo = ctk.CTkLabel(
            wiersz_logo, text="Nie wybrano", font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_logo.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        ctk.CTkButton(
            wiersz_logo, text="Wybierz plik...", font=styl.CZCIONKA_DROBNA, width=110,
            fg_color="transparent", border_width=1, border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY, hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._wybierz_logo,
        ).grid(row=0, column=1)

        self._etykieta_pola(wewnatrz, "Domyślna stawka VAT na fakturach")
        self._var_domyslna_stawka_vat = ctk.StringVar(value=formatowanie.ETYKIETY_STAWEK_VAT["23"])
        ctk.CTkOptionMenu(
            wewnatrz, values=_ETYKIETY_STAWEK_VAT, variable=self._var_domyslna_stawka_vat,
            font=styl.CZCIONKA_TRESC, fg_color=styl.KOLOR_AKCENT, button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        # -- sprzedaz ponizej stanu magazynowego (Faza 8) - konfigurowalne wg
        # PLAN_PROJEKTU.md 3.5, ale do teraz appka zawsze dzialala w trybie
        # domyslnym OSTRZEGAJ bez mozliwosci zmiany - to pole na to naprawia. ---
        ctk.CTkFrame(wewnatrz, fg_color=styl.KOLOR_OBRAMOWANIE, height=1).pack(
            fill="x", pady=styl.ODSTEP_SREDNI
        )
        ctk.CTkLabel(
            wewnatrz, text="Sprzedaż poniżej stanu magazynowego", font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        self._var_tryb_blokady = ctk.StringVar(value=ETYKIETA_OSTRZEGAJ)
        ctk.CTkSegmentedButton(
            wewnatrz,
            values=[ETYKIETA_OSTRZEGAJ, ETYKIETA_BLOKUJ],
            variable=self._var_tryb_blokady,
            font=styl.CZCIONKA_TRESC,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        # -- dane do JPK_V7 (Faza 13) - forma prawna okresla ksztalt sekcji
        # Podmiot1: osoba fizyczna (JDG) potrzebuje imie/nazwisko/date urodzenia,
        # spolka - samej nazwy (juz wpisanej powyzej jako "Nazwa"). Kod urzedu
        # jest wspolny dla obu i wymagany zawsze. -------------------------------
        ctk.CTkFrame(wewnatrz, fg_color=styl.KOLOR_OBRAMOWANIE, height=1).pack(
            fill="x", pady=styl.ODSTEP_SREDNI
        )
        ctk.CTkLabel(
            wewnatrz, text="Dane do JPK_V7", font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Forma prawna")
        self._var_typ_podatnika = ctk.StringVar(value=ETYKIETA_SPOLKA)
        ctk.CTkSegmentedButton(
            wewnatrz,
            values=[ETYKIETA_JDG, ETYKIETA_SPOLKA],
            variable=self._var_typ_podatnika,
            font=styl.CZCIONKA_TRESC,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._na_zmiane_typ_podatnika,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._ramka_osoba_fizyczna = ctk.CTkFrame(wewnatrz, fg_color="transparent")

        self._etykieta_pola(self._ramka_osoba_fizyczna, "Imię")
        self._pole_imie = ctk.CTkEntry(self._ramka_osoba_fizyczna, font=styl.CZCIONKA_TRESC)
        self._pole_imie.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(self._ramka_osoba_fizyczna, "Nazwisko")
        self._pole_nazwisko = ctk.CTkEntry(self._ramka_osoba_fizyczna, font=styl.CZCIONKA_TRESC)
        self._pole_nazwisko.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(self._ramka_osoba_fizyczna, "Data urodzenia (RRRR-MM-DD)")
        self._pole_data_urodzenia = ctk.CTkEntry(self._ramka_osoba_fizyczna, font=styl.CZCIONKA_TRESC)
        self._pole_data_urodzenia.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Urząd skarbowy")
        wiersz_us = ctk.CTkFrame(wewnatrz, fg_color="transparent")
        wiersz_us.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        wiersz_us.grid_columnconfigure(0, weight=1)

        self._urzad_wybrany: dict | None = None
        self._urzedy_cache: list[dict] = []
        self._etykieta_urzad = ctk.CTkLabel(
            wiersz_us, text="Nie wybrano", font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_urzad.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        ctk.CTkButton(
            wiersz_us,
            text="Wybierz...",
            font=styl.CZCIONKA_DROBNA,
            width=90,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._otworz_wybor_urzedu,
        ).grid(row=0, column=1)

        self._przycisk_firma = ctk.CTkButton(
            wewnatrz,
            text="Zapisz dane firmy",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz_firme,
        )
        self._przycisk_firma.pack(fill="x", pady=(styl.ODSTEP_MALY, 0))

        self._na_zmiane_typ_podatnika(self._var_typ_podatnika.get())
        self._wczytaj_firme()
        self._wczytaj_urzedy_skarbowe()

    def _na_zmiane_typ_podatnika(self, _wartosc: str) -> None:
        if self._var_typ_podatnika.get() == ETYKIETA_JDG:
            self._ramka_osoba_fizyczna.pack(fill="x", before=self._przycisk_firma)
        else:
            self._ramka_osoba_fizyczna.pack_forget()

    def _wczytaj_urzedy_skarbowe(self) -> None:
        def zadanie():
            return api_client.pobierz_urzedy_skarbowe()

        def sukces(urzedy: list[dict]) -> None:
            self._urzedy_cache = urzedy
            if self._urzad_wybrany and not self._urzad_wybrany.get("nazwa"):
                dopasowany = next(
                    (u for u in urzedy if u["kod"] == self._urzad_wybrany["kod"]), None
                )
                if dopasowany:
                    self._ustaw_wybrany_urzad(dopasowany)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _otworz_wybor_urzedu(self) -> None:
        if not self._urzedy_cache:
            komunikat_bledu(self, "Lista urzędów skarbowych jeszcze się wczytuje - spróbuj ponownie za chwilę.")
            return
        DialogWyboruUrzeduSkarbowego(self, self._urzedy_cache, on_wybierz=self._ustaw_wybrany_urzad)

    def _ustaw_wybrany_urzad(self, urzad: dict) -> None:
        self._urzad_wybrany = urzad
        self._etykieta_urzad.configure(
            text=f"{urzad['kod']} — {urzad['nazwa'].title()}", text_color=styl.KOLOR_TEKST_GLOWNY
        )

    def _wczytaj_firme(self) -> None:
        def zadanie():
            return api_client.pobierz_firme()

        def sukces(firma: dict) -> None:
            self._firma_istnieje = True
            self._przycisk_firma.configure(text="Zapisz zmiany")
            for klucz, wpis in self._pola_firmy.items():
                wartosc = firma.get(klucz)
                if wartosc:
                    wpis.delete(0, "end")
                    wpis.insert(0, str(wartosc))

            self._var_typ_podatnika.set(
                ETYKIETA_JDG if firma.get("typ_podatnika") == "osoba_fizyczna" else ETYKIETA_SPOLKA
            )
            self._na_zmiane_typ_podatnika(self._var_typ_podatnika.get())
            self._var_tryb_blokady.set(
                ETYKIETA_BLOKUJ if firma.get("tryb_blokady_ujemnego_stanu") == "blokuj" else ETYKIETA_OSTRZEGAJ
            )
            stawka_vat = firma.get("domyslna_stawka_vat")
            if stawka_vat in formatowanie.ETYKIETY_STAWEK_VAT:
                self._var_domyslna_stawka_vat.set(formatowanie.ETYKIETY_STAWEK_VAT[stawka_vat])
            if firma.get("logo_path"):
                self._logo_sciezka = firma["logo_path"]
                self._etykieta_logo.configure(
                    text=Path(firma["logo_path"]).name, text_color=styl.KOLOR_TEKST_GLOWNY
                )
            if firma.get("imie_pierwsze"):
                self._pole_imie.delete(0, "end")
                self._pole_imie.insert(0, firma["imie_pierwsze"])
            if firma.get("nazwisko"):
                self._pole_nazwisko.delete(0, "end")
                self._pole_nazwisko.insert(0, firma["nazwisko"])
            if firma.get("data_urodzenia"):
                self._pole_data_urodzenia.delete(0, "end")
                self._pole_data_urodzenia.insert(0, firma["data_urodzenia"])
            if firma.get("kod_urzedu_skarbowego"):
                # Nazwa doklei sie pozniej w _wczytaj_urzedy_skarbowe, jesli
                # lista urzedow jeszcze sie nie wczytala w tym momencie.
                dopasowany = next(
                    (u for u in self._urzedy_cache if u["kod"] == firma["kod_urzedu_skarbowego"]), None
                )
                self._ustaw_wybrany_urzad(dopasowany or {"kod": firma["kod_urzedu_skarbowego"], "nazwa": ""})

        def blad(e: api_client.ApiError) -> None:
            if e.status_code != 404:
                komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _pobierz_firme_z_gus(self) -> None:
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
                    self._pola_firmy[klucz_pola].delete(0, "end")
                    self._pola_firmy[klucz_pola].insert(0, wartosc)

        pobierz_z_gus(
            self,
            self._pola_firmy["nip"].get(),
            self._przycisk_gus_firmy,
            self._banner_firmy,
            wypelnij,
        )

    def _wybierz_logo(self) -> None:
        sciezka = wybierz_i_skopiuj_logo(self)
        if sciezka:
            self._logo_sciezka = sciezka
            self._etykieta_logo.configure(text=Path(sciezka).name, text_color=styl.KOLOR_TEKST_GLOWNY)

    def _zapisz_firme(self) -> None:
        nazwa = self._pola_firmy["nazwa"].get().strip()
        nip = self._pola_firmy["nip"].get().strip()
        if not nazwa or not nip:
            self._banner_firmy.pokaz("Nazwa i NIP firmy są wymagane.")
            return

        jest_jdg = self._var_typ_podatnika.get() == ETYKIETA_JDG
        imie = self._pole_imie.get().strip()
        nazwisko = self._pole_nazwisko.get().strip()
        data_urodzenia_tekst = self._pole_data_urodzenia.get().strip()
        data_urodzenia_parsed: date | None = None
        if jest_jdg:
            if not (imie and nazwisko and data_urodzenia_tekst):
                self._banner_firmy.pokaz(
                    "Dla osoby fizycznej (JDG) wymagane są imię, nazwisko i data urodzenia (do JPK_V7)."
                )
                return
            try:
                data_urodzenia_parsed = date.fromisoformat(data_urodzenia_tekst)
            except ValueError:
                self._banner_firmy.pokaz("Data urodzenia musi być w formacie RRRR-MM-DD.")
                return
        self._banner_firmy.ukryj()

        dane = {
            "nazwa": nazwa,
            "nip": nip,
            "typ_podatnika": "osoba_fizyczna" if jest_jdg else "osoba_niefizyczna",
            "tryb_blokady_ujemnego_stanu": (
                "blokuj" if self._var_tryb_blokady.get() == ETYKIETA_BLOKUJ else "ostrzegaj"
            ),
            "domyslna_stawka_vat": _KLUCZE_WG_ETYKIETY_STAWKI_VAT[self._var_domyslna_stawka_vat.get()],
        }
        if self._logo_sciezka:
            dane["logo_path"] = self._logo_sciezka
        for klucz in (
            "ulica", "kod_pocztowy", "miejscowosc", "kraj", "email", "telefon",
            "bank_nazwa", "bank_numer_konta", "bank_numer_konta_vat",
        ):
            wartosc = self._pola_firmy[klucz].get().strip()
            if wartosc:
                dane[klucz] = wartosc
        if jest_jdg:
            dane["imie_pierwsze"] = imie
            dane["nazwisko"] = nazwisko
            dane["data_urodzenia"] = data_urodzenia_parsed.isoformat()
        if self._urzad_wybrany:
            dane["kod_urzedu_skarbowego"] = self._urzad_wybrany["kod"]

        ustaw_tekst_ladowania(self._przycisk_firma, True, "Zapisz dane firmy")

        def zadanie():
            if self._firma_istnieje:
                return api_client.aktualizuj_firme(dane)
            return api_client.utworz_firme(dane)

        def sukces(_wynik) -> None:
            self._firma_istnieje = True
            ustaw_tekst_ladowania(self._przycisk_firma, False, "Zapisz zmiany")
            pokaz_toast(self, "Dane firmy zapisane.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(
                self._przycisk_firma, False,
                "Zapisz zmiany" if self._firma_istnieje else "Zapisz dane firmy",
            )
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    # -- kopia zapasowa i przywracanie (Faza 22) - KRYTYCZNY priorytet, appka
    # przechowuje od Fazy 18B wszystkie dane firmy wylacznie lokalnie -------

    def _zbuduj_karte_backupu(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Kopia zapasowa i przywracanie",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        ctk.CTkLabel(
            wewnatrz,
            text=(
                "Kopia obejmuje całą bazę danych (faktury, klientów, magazyn) "
                "oraz logo firmy, zaszyfrowana hasłem, które ustawiasz osobno "
                "od hasła logowania. Zalecane: wybierz lokalizację NA INNYM "
                "nośniku niż ten komputer - dysk USB, dysk sieciowy albo "
                "folder synchronizowany z chmurą (Google Drive/OneDrive/"
                "Dropbox)."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=320,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._etykieta_pola(wewnatrz, "Lokalizacja kopii zapasowych")
        wiersz_katalog = ctk.CTkFrame(wewnatrz, fg_color="transparent")
        wiersz_katalog.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        wiersz_katalog.grid_columnconfigure(0, weight=1)
        self._etykieta_katalog_backupu = ctk.CTkLabel(
            wiersz_katalog, text="Nie wybrano", font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_katalog_backupu.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        ctk.CTkButton(
            wiersz_katalog, text="Wybierz folder...", font=styl.CZCIONKA_DROBNA, width=110,
            fg_color="transparent", border_width=1, border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY, hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._wybierz_katalog_backupu,
        ).grid(row=0, column=1)

        self._etykieta_stan_backupu = ctk.CTkLabel(
            wewnatrz, text="", font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_stan_backupu.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk_wykonaj_backup = ctk.CTkButton(
            wewnatrz,
            text="Wykonaj kopię zapasową teraz",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._otworz_wykonanie_backupu,
        )
        self._przycisk_wykonaj_backup.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        ctk.CTkFrame(wewnatrz, fg_color=styl.KOLOR_OBRAMOWANIE, height=1).pack(
            fill="x", pady=styl.ODSTEP_SREDNI
        )

        ctk.CTkLabel(
            wewnatrz, text="Przywracanie z kopii zapasowej", font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        ctk.CTkLabel(
            wewnatrz,
            text="Nadpisuje CAŁKOWICIE bieżące dane wybraną kopią zapasową.",
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=320,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        ctk.CTkButton(
            wewnatrz,
            text="Przywróć z kopii zapasowej...",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_BLAD,
            text_color=styl.KOLOR_BLAD,
            hover_color=styl.KOLOR_BLAD_TLO,
            command=lambda: DialogPrzywrocBackup(self),
        ).pack(fill="x")

        self._odswiez_stan_backupu()

    def _odswiez_stan_backupu(self) -> None:
        stan = kz.stan_backupu()
        katalog = stan["katalog_docelowy"]
        if katalog:
            self._etykieta_katalog_backupu.configure(text=katalog, text_color=styl.KOLOR_TEKST_GLOWNY)
        else:
            self._etykieta_katalog_backupu.configure(text="Nie wybrano", text_color=styl.KOLOR_TEKST_DRUGORZEDNY)

        if stan["ostatni_backup"] is None:
            self._etykieta_stan_backupu.configure(
                text="Nie wykonano jeszcze żadnej kopii zapasowej.", text_color=styl.KOLOR_OSTRZEZENIE
            )
        else:
            dni = stan["dni_od_ostatniego"]
            data_tekst = formatowanie.formatuj_data_czas(
                datetime.fromisoformat(stan["ostatni_backup"])
            )
            opis_dni = "dzisiaj" if dni == 0 else f"{dni} dni temu"
            self._etykieta_stan_backupu.configure(
                text=f"Ostatnia kopia zapasowa: {data_tekst} ({opis_dni}).",
                text_color=styl.KOLOR_BLAD if stan["przeterminowany"] else styl.KOLOR_SUKCES,
            )

        self._przycisk_wykonaj_backup.configure(state="normal" if katalog else "disabled")

    def _wybierz_katalog_backupu(self) -> None:
        katalog = filedialog.askdirectory(parent=self, title="Wybierz lokalizację kopii zapasowych")
        if not katalog:
            return
        kz.ustaw_katalog_docelowy(katalog)
        self._odswiez_stan_backupu()

    def _otworz_wykonanie_backupu(self) -> None:
        stan = kz.stan_backupu()
        if not stan["katalog_docelowy"]:
            return
        DialogWykonajBackup(
            self, stan["katalog_docelowy"], on_wykonano=self._odswiez_stan_backupu
        )

    # -- integracja GUS (srodowisko testowe/produkcyjne + klucz) -------------

    def _zbuduj_karte_integracji_gus(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Integracja GUS (REGON)",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        ctk.CTkLabel(
            wewnatrz,
            text=(
                "Domyślnie środowisko testowe (publiczny klucz testowy GUS, "
                "przykładowe dane). Środowisko produkcyjne wymaga własnego "
                "klucza - wniosek o klucz wysyła się do GUS "
                "(regon_bir@stat.gov.pl)."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=320,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._etykieta_pola(wewnatrz, "Środowisko")
        self._var_srodowisko_gus = ctk.StringVar(value="Testowe")
        ctk.CTkSegmentedButton(
            wewnatrz,
            values=["Testowe", "Produkcyjne"],
            variable=self._var_srodowisko_gus,
            font=styl.CZCIONKA_TRESC,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Klucz produkcyjny")
        self._pole_klucz_gus = ctk.CTkEntry(
            wewnatrz, show="•", font=styl.CZCIONKA_TRESC,
            placeholder_text="(zapisany - wpisz nowy, żeby zmienić)",
        )
        self._pole_klucz_gus.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_stan_klucza_gus = ctk.CTkLabel(
            wewnatrz, text="", font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_stan_klucza_gus.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._przycisk_gus_ustawienia = ctk.CTkButton(
            wewnatrz,
            text="Zapisz ustawienia GUS",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz_ustawienia_gus,
        )
        self._przycisk_gus_ustawienia.pack(fill="x")

        self._wczytaj_ustawienia_gus()

    def _wczytaj_ustawienia_gus(self) -> None:
        def zadanie():
            return api_client.pobierz_ustawienia_gus()

        def sukces(dane: dict) -> None:
            self._var_srodowisko_gus.set(
                "Produkcyjne" if dane["srodowisko"] == "produkcyjne" else "Testowe"
            )
            self._etykieta_stan_klucza_gus.configure(
                text=(
                    "Klucz produkcyjny zapisany."
                    if dane["ma_klucz_produkcyjny"]
                    else "Brak zapisanego klucza produkcyjnego - używany jest klucz testowy."
                )
            )

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zapisz_ustawienia_gus(self) -> None:
        srodowisko = "produkcyjne" if self._var_srodowisko_gus.get() == "Produkcyjne" else "testowe"
        dane: dict = {"srodowisko": srodowisko}
        klucz_nowy = self._pole_klucz_gus.get().strip()
        if klucz_nowy:
            dane["klucz_produkcyjny"] = klucz_nowy

        self._przycisk_gus_ustawienia.configure(state="disabled")

        def zadanie():
            return api_client.zapisz_ustawienia_gus(dane)

        def sukces(wynik: dict) -> None:
            self._przycisk_gus_ustawienia.configure(state="normal")
            self._pole_klucz_gus.delete(0, "end")
            self._etykieta_stan_klucza_gus.configure(
                text=(
                    "Klucz produkcyjny zapisany."
                    if wynik["ma_klucz_produkcyjny"]
                    else "Brak zapisanego klucza produkcyjnego - używany jest klucz testowy."
                )
            )
            pokaz_toast(self, "Ustawienia GUS zapisane.")

        def blad(e: api_client.ApiError) -> None:
            self._przycisk_gus_ustawienia.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    # -- integracja KSeF (Faza 12A - fundament + uwierzytelnienie, bez
    # wysylki faktur) - srodowisko testowe/produkcyjne z wyraznym oznaczeniem
    # aktywnego, bo to prawdziwy system rzadowy (pomylka srodowiska ma
    # konsekwencje prawne/finansowe), token przechowywany zaszyfrowany
    # (app/services/ksef_ustawienia.py, Windows DPAPI) ----------------------

    def _zbuduj_karte_ksef(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Integracja KSeF",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        self._banda_srodowiska_ksef = ctk.CTkLabel(
            wewnatrz,
            text="",
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            corner_radius=styl.PROMIEN_NAROZNIKA,
        )
        self._banda_srodowiska_ksef.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI), ipady=styl.ODSTEP_MALY)

        ctk.CTkLabel(
            wewnatrz,
            text=(
                "Domyślnie środowisko TESTOWE Ministerstwa Finansów (sandbox KSeF 2.0). "
                "Przełączenie na PRODUKCYJNE wysyła żądania do prawdziwego systemu "
                "rządowego i wymaga potwierdzenia."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=320,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._etykieta_pola(wewnatrz, "Środowisko")
        self._var_srodowisko_ksef = ctk.StringVar(value="Testowe")
        self._przelacznik_srodowiska_ksef = ctk.CTkSegmentedButton(
            wewnatrz,
            values=["Testowe", "Produkcyjne"],
            variable=self._var_srodowisko_ksef,
            font=styl.CZCIONKA_TRESC,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._na_zmiane_srodowiska_ksef,
        )
        self._przelacznik_srodowiska_ksef.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Token KSeF")
        self._pole_token_ksef = ctk.CTkEntry(
            wewnatrz, show="•", font=styl.CZCIONKA_TRESC,
            placeholder_text="(zapisany - wpisz nowy, żeby zmienić)",
        )
        self._pole_token_ksef.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_stan_tokena_ksef = ctk.CTkLabel(
            wewnatrz, text="", font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_stan_tokena_ksef.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        # Faza 12C - w odroznieniu od reszty ustawien KSeF powyzej (srodowisko,
        # token), to WLACZA rzeczywiste polaczenie sieciowe z KSeF przy kazdym
        # starcie appki - stad domyslnie wylaczone, uzytkownik decyduje swiadomie.
        self._var_sprawdzaj_koszty_przy_starcie = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            wewnatrz,
            text="Sprawdzaj nowe faktury kosztowe w KSeF przy starcie aplikacji",
            font=styl.CZCIONKA_TRESC,
            variable=self._var_sprawdzaj_koszty_przy_starcie,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY), anchor="w")

        self._etykieta_ostatnie_sprawdzenie_kosztow = ctk.CTkLabel(
            wewnatrz, text="", font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_ostatnie_sprawdzenie_kosztow.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk_ksef_zapisz = ctk.CTkButton(
            wewnatrz,
            text="Zapisz ustawienia KSeF",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zapisz_ustawienia_ksef,
        )
        self._przycisk_ksef_zapisz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._banner_ksef = Banner(wewnatrz)
        self._banner_ksef.ustaw_geometrie(
            lambda: self._banner_ksef.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        )

        self._przycisk_ksef_testuj = ctk.CTkButton(
            wewnatrz,
            text="Testuj połączenie z KSeF",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._testuj_polaczenie_ksef,
        )
        self._przycisk_ksef_testuj.pack(fill="x")

        self._wczytaj_ustawienia_ksef()

    def _odswiez_banda_srodowiska_ksef(self, srodowisko: str) -> None:
        tekst, kolor_tekstu, kolor_tla = formatuj_srodowisko_ksef(srodowisko)
        self._banda_srodowiska_ksef.configure(
            text=tekst, fg_color=kolor_tla, text_color=kolor_tekstu,
        )

    def _na_zmiane_srodowiska_ksef(self, wartosc: str) -> None:
        if wartosc == "Produkcyjne":
            potwierdzono = messagebox.askyesno(
                "Przełączenie na środowisko produkcyjne KSeF",
                "Zamierzasz przełączyć integrację KSeF na ŚRODOWISKO PRODUKCYJNE.\n\n"
                "Od tego momentu żądania (w tym test połączenia) będą wysyłane do "
                "prawdziwego systemu Ministerstwa Finansów, z rzeczywistymi "
                "konsekwencjami prawnymi i finansowymi.\n\n"
                "Czy na pewno chcesz kontynuować?",
                parent=self,
            )
            if not potwierdzono:
                self._przelacznik_srodowiska_ksef.set("Testowe")
                wartosc = "Testowe"
        self._odswiez_banda_srodowiska_ksef(
            "produkcyjne" if wartosc == "Produkcyjne" else "testowe"
        )

    def _wczytaj_ustawienia_ksef(self) -> None:
        def zadanie():
            return api_client.pobierz_ustawienia_ksef()

        def sukces(dane: dict) -> None:
            srodowisko = dane["srodowisko"]
            self._przelacznik_srodowiska_ksef.set(
                "Produkcyjne" if srodowisko == "produkcyjne" else "Testowe"
            )
            self._odswiez_banda_srodowiska_ksef(srodowisko)
            self._var_sprawdzaj_koszty_przy_starcie.set(
                dane.get("sprawdzaj_koszty_przy_starcie", False)
            )
            self._zastosuj_stan_tokena_i_sprawdzenia(dane)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zastosuj_stan_tokena_i_sprawdzenia(self, dane: dict) -> None:
        if dane["ma_token"]:
            podglad = dane.get("token_podglad")
            tekst_tokena = (
                f"Token KSeF zapisany (zaszyfrowany lokalnie), kończy się na „...{podglad}”."
                if podglad
                else "Token KSeF zapisany (zaszyfrowany lokalnie)."
            )
            self._pole_token_ksef.configure(
                placeholder_text=f"(zapisany, ...{podglad} - wpisz nowy, żeby zmienić)"
                if podglad
                else "(zapisany - wpisz nowy, żeby zmienić)"
            )
        else:
            tekst_tokena = "Brak zapisanego tokena KSeF."
            self._pole_token_ksef.configure(placeholder_text="Wklej token KSeF...")
        self._etykieta_stan_tokena_ksef.configure(text=tekst_tokena)

        ostatnie = dane.get("ostatnie_sprawdzenie_kosztow")
        self._etykieta_ostatnie_sprawdzenie_kosztow.configure(
            text=(
                f"Ostatnie sprawdzenie faktur kosztowych: {formatowanie.formatuj_data_czas(ostatnie)}"
                if ostatnie
                else "Faktury kosztowe nie były jeszcze sprawdzane."
            )
        )

    def _zapisz_ustawienia_ksef(self) -> None:
        srodowisko = (
            "produkcyjne" if self._var_srodowisko_ksef.get() == "Produkcyjne" else "testowe"
        )
        dane: dict = {
            "srodowisko": srodowisko,
            "sprawdzaj_koszty_przy_starcie": self._var_sprawdzaj_koszty_przy_starcie.get(),
        }
        token_nowy = self._pole_token_ksef.get().strip()
        if token_nowy:
            dane["token"] = token_nowy

        self._przycisk_ksef_zapisz.configure(state="disabled")

        def zadanie():
            return api_client.zapisz_ustawienia_ksef(dane)

        def sukces(wynik: dict) -> None:
            self._przycisk_ksef_zapisz.configure(state="normal")
            self._pole_token_ksef.delete(0, "end")
            self._odswiez_banda_srodowiska_ksef(wynik["srodowisko"])
            self._zastosuj_stan_tokena_i_sprawdzenia(wynik)
            pokaz_toast(self, "Ustawienia KSeF zapisane.")

        def blad(e: api_client.ApiError) -> None:
            self._przycisk_ksef_zapisz.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _testuj_polaczenie_ksef(self) -> None:
        self._banner_ksef.ukryj()
        ustaw_tekst_ladowania(
            self._przycisk_ksef_testuj, True, "Testuj połączenie z KSeF", "Łączenie z KSeF..."
        )

        def zadanie():
            return api_client.testuj_polaczenie_ksef()

        def sukces(wynik: dict) -> None:
            ustaw_tekst_ladowania(self._przycisk_ksef_testuj, False, "Testuj połączenie z KSeF")
            if wynik["powodzenie"]:
                pokaz_toast(self, wynik["komunikat"], "sukces")
            else:
                self._banner_ksef.pokaz(wynik["komunikat"])

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_ksef_testuj, False, "Testuj połączenie z KSeF")
            self._banner_ksef.pokaz(e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    # -- konfiguracja poczty SMTP (Faza 23) - fundament pod przypomnienia o
    # platnosciach ponizej. Appka NIE MIALA zadnej infrastruktury wysylki
    # e-mail przed ta faza, mimo ze byla zaplanowana dla Etapu 1 -------------

    def _zbuduj_karte_email(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Konfiguracja poczty (SMTP)",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        ctk.CTkLabel(
            wewnatrz,
            text="Wymagana do wysyłki przypomnień o płatnościach (poniżej).",
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=320,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._banner_email = Banner(wewnatrz)
        self._banner_email.ustaw_geometrie(
            lambda: self._banner_email.pack(fill="x", pady=(0, styl.ODSTEP_MALY), before=self._pierwsze_pole_email)
        )

        self._etykieta_pola(wewnatrz, "Serwer SMTP (host)")
        self._pole_email_host = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC)
        self._pole_email_host.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        self._pierwsze_pole_email = self._pole_email_host

        self._etykieta_pola(wewnatrz, "Port")
        self._pole_email_port = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC)
        self._pole_email_port.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Szyfrowanie")
        self._var_email_szyfrowanie = ctk.StringVar(value="STARTTLS")
        ctk.CTkSegmentedButton(
            wewnatrz,
            values=["STARTTLS", "SSL", "Brak"],
            variable=self._var_email_szyfrowanie,
            font=styl.CZCIONKA_TRESC,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Użytkownik (login)")
        self._pole_email_uzytkownik = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC)
        self._pole_email_uzytkownik.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Hasło")
        self._pole_email_haslo = ctk.CTkEntry(
            wewnatrz, show="•", font=styl.CZCIONKA_TRESC,
            placeholder_text="(zapisane - wpisz nowe, żeby zmienić)",
        )
        self._pole_email_haslo.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Adres nadawcy (opcjonalnie, domyślnie = login)")
        self._pole_email_nadawca_adres = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC)
        self._pole_email_nadawca_adres.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Nazwa nadawcy (opcjonalnie)")
        self._pole_email_nadawca_nazwa = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC)
        self._pole_email_nadawca_nazwa.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk_email_zapisz = ctk.CTkButton(
            wewnatrz, text="Zapisz ustawienia poczty", fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER, command=self._zapisz_ustawienia_email,
        )
        self._przycisk_email_zapisz.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._przycisk_email_testuj = ctk.CTkButton(
            wewnatrz, text="Testuj połączenie", fg_color="transparent", border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE, text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY, command=self._testuj_polaczenie_email,
        )
        self._przycisk_email_testuj.pack(fill="x")

        self._wczytaj_ustawienia_email()

    def _wczytaj_ustawienia_email(self) -> None:
        def zadanie():
            return api_client.pobierz_ustawienia_email()

        def sukces(dane: dict) -> None:
            if dane.get("host"):
                self._pole_email_host.insert(0, dane["host"])
            self._pole_email_port.insert(0, str(dane.get("port", 587)))
            if dane.get("uzytkownik"):
                self._pole_email_uzytkownik.insert(0, dane["uzytkownik"])
            if dane.get("nadawca_adres"):
                self._pole_email_nadawca_adres.insert(0, dane["nadawca_adres"])
            if dane.get("nadawca_nazwa"):
                self._pole_email_nadawca_nazwa.insert(0, dane["nadawca_nazwa"])
            self._var_email_szyfrowanie.set(
                {"starttls": "STARTTLS", "ssl": "SSL", "brak": "Brak"}.get(
                    dane.get("szyfrowanie", "starttls"), "STARTTLS"
                )
            )
            if dane.get("ma_haslo"):
                self._pole_email_haslo.configure(placeholder_text="(zapisane - wpisz nowe, żeby zmienić)")
            else:
                self._pole_email_haslo.configure(placeholder_text="Wpisz hasło...")

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zapisz_ustawienia_email(self) -> None:
        self._banner_email.ukryj()
        port_tekst = self._pole_email_port.get().strip()
        try:
            port = int(port_tekst) if port_tekst else 587
        except ValueError:
            self._banner_email.pokaz("Port musi być liczbą całkowitą.")
            return

        dane: dict = {
            "host": self._pole_email_host.get().strip(),
            "port": port,
            "uzytkownik": self._pole_email_uzytkownik.get().strip(),
            "szyfrowanie": {"STARTTLS": "starttls", "SSL": "ssl", "Brak": "brak"}[
                self._var_email_szyfrowanie.get()
            ],
        }
        haslo = self._pole_email_haslo.get()
        if haslo:
            dane["haslo"] = haslo
        nadawca_adres = self._pole_email_nadawca_adres.get().strip()
        if nadawca_adres:
            dane["nadawca_adres"] = nadawca_adres
        nadawca_nazwa = self._pole_email_nadawca_nazwa.get().strip()
        if nadawca_nazwa:
            dane["nadawca_nazwa"] = nadawca_nazwa

        ustaw_tekst_ladowania(self._przycisk_email_zapisz, True, "Zapisz ustawienia poczty")

        def zadanie():
            return api_client.zapisz_ustawienia_email(dane)

        def sukces(wynik: dict) -> None:
            ustaw_tekst_ladowania(self._przycisk_email_zapisz, False, "Zapisz ustawienia poczty")
            self._pole_email_haslo.delete(0, "end")
            if wynik.get("ma_haslo"):
                self._pole_email_haslo.configure(placeholder_text="(zapisane - wpisz nowe, żeby zmienić)")
            pokaz_toast(self, "Ustawienia poczty zapisane.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_email_zapisz, False, "Zapisz ustawienia poczty")
            self._banner_email.pokaz(e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _testuj_polaczenie_email(self) -> None:
        self._banner_email.ukryj()
        ustaw_tekst_ladowania(self._przycisk_email_testuj, True, "Testuj połączenie", "Łączenie...")

        def zadanie():
            return api_client.testuj_polaczenie_email()

        def sukces(wynik: dict) -> None:
            ustaw_tekst_ladowania(self._przycisk_email_testuj, False, "Testuj połączenie")
            if wynik["powodzenie"]:
                pokaz_toast(self, wynik["komunikat"], "sukces")
            else:
                self._banner_email.pokaz(wynik["komunikat"])

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_email_testuj, False, "Testuj połączenie")
            self._banner_email.pokaz(e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    # -- przypomnienia o platnosciach (Faza 23) -------------------------------

    def _zbuduj_karte_przypomnien(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Przypomnienia o płatnościach",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        ctk.CTkLabel(
            wewnatrz,
            text=(
                "Każdy z trzech rodzajów przypomnienia można włączyć niezależnie. "
                "Appka NIGDY nie wysyła nic automatycznie - przy starcie pokazuje "
                "listę do zatwierdzenia (jak faktury cykliczne)."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=320,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._banner_przypomnienia = Banner(wewnatrz)
        self._banner_przypomnienia.ustaw_geometrie(
            lambda: self._banner_przypomnienia.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        )

        self._etykieta_pola(wewnatrz, "Dni przed terminem (puste = wyłączone)")
        self._pole_dni_przed = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC, placeholder_text="np. 3")
        self._pole_dni_przed.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._var_w_dniu_terminu = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            wewnatrz, text="Wysyłaj w dniu terminu płatności", font=styl.CZCIONKA_TRESC,
            variable=self._var_w_dniu_terminu, fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY), anchor="w")

        self._etykieta_pola(wewnatrz, "Dni po terminie - ponaglenie (puste = wyłączone)")
        self._pole_dni_po = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC, placeholder_text="np. 7")
        self._pole_dni_po.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkFrame(wewnatrz, fg_color=styl.KOLOR_OBRAMOWANIE, height=1).pack(
            fill="x", pady=(0, styl.ODSTEP_SREDNI)
        )

        self._etykieta_pola(wewnatrz, "Temat wiadomości")
        self._pole_szablon_temat = ctk.CTkEntry(
            wewnatrz, font=styl.CZCIONKA_TRESC,
            placeholder_text="Przypomnienie o płatności — faktura {numer_faktury}",
        )
        self._pole_szablon_temat.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Treść wiadomości")
        self._pole_szablon_tresc = ctk.CTkTextbox(wewnatrz, height=140, font=styl.CZCIONKA_TRESC)
        self._pole_szablon_tresc.pack(fill="x", pady=(0, styl.ODSTEP_MIKRO))

        ctk.CTkLabel(
            wewnatrz,
            text=(
                "Dostępne pola: {numer_faktury} {kwota_pozostala} {termin_platnosci} "
                "{nazwa_firmy} {nazwa_klienta} {typ_przypomnienia}. Puste pola = "
                "użyty zostanie wbudowany szablon domyślny."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=320,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk_przypomnienia_zapisz = ctk.CTkButton(
            wewnatrz, text="Zapisz ustawienia przypomnień", fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER, command=self._zapisz_ustawienia_przypomnien,
        )
        self._przycisk_przypomnienia_zapisz.pack(fill="x")

        self._wczytaj_ustawienia_przypomnien()

    def _wczytaj_ustawienia_przypomnien(self) -> None:
        def zadanie():
            return api_client.pobierz_firme()

        def sukces(firma: dict) -> None:
            if firma.get("przypomnienia_dni_przed") is not None:
                self._pole_dni_przed.insert(0, str(firma["przypomnienia_dni_przed"]))
            self._var_w_dniu_terminu.set(bool(firma.get("przypomnienia_w_dniu_terminu")))
            if firma.get("przypomnienia_dni_po") is not None:
                self._pole_dni_po.insert(0, str(firma["przypomnienia_dni_po"]))
            if firma.get("przypomnienia_szablon_temat"):
                self._pole_szablon_temat.insert(0, firma["przypomnienia_szablon_temat"])
            if firma.get("przypomnienia_szablon_tresc"):
                self._pole_szablon_tresc.insert("1.0", firma["przypomnienia_szablon_tresc"])

        def blad(e: api_client.ApiError) -> None:
            if e.status_code != 404:
                komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zapisz_ustawienia_przypomnien(self) -> None:
        self._banner_przypomnienia.ukryj()

        def parsuj_dni(tekst: str, nazwa: str) -> int | None:
            tekst = tekst.strip()
            if not tekst:
                return None
            if not tekst.isdigit():
                raise ValueError(f"„{nazwa}” musi być liczbą całkowitą nieujemną.")
            return int(tekst)

        try:
            dni_przed = parsuj_dni(self._pole_dni_przed.get(), "Dni przed terminem")
            dni_po = parsuj_dni(self._pole_dni_po.get(), "Dni po terminie")
        except ValueError as e:
            self._banner_przypomnienia.pokaz(str(e))
            return

        dane: dict = {
            "przypomnienia_dni_przed": dni_przed,
            "przypomnienia_w_dniu_terminu": bool(self._var_w_dniu_terminu.get()),
            "przypomnienia_dni_po": dni_po,
            "przypomnienia_szablon_temat": self._pole_szablon_temat.get().strip() or None,
            "przypomnienia_szablon_tresc": self._pole_szablon_tresc.get("1.0", "end-1c").strip() or None,
        }

        ustaw_tekst_ladowania(self._przycisk_przypomnienia_zapisz, True, "Zapisz ustawienia przypomnień")

        def zadanie():
            if not self._firma_istnieje:
                raise api_client.ApiError(
                    "Uzupełnij najpierw dane firmy (karta „Dane firmy” powyżej)."
                )
            return api_client.aktualizuj_firme(dane)

        def sukces(_wynik) -> None:
            ustaw_tekst_ladowania(self._przycisk_przypomnienia_zapisz, False, "Zapisz ustawienia przypomnień")
            pokaz_toast(self, "Ustawienia przypomnień zapisane.")

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_przypomnienia_zapisz, False, "Zapisz ustawienia przypomnień")
            self._banner_przypomnienia.pokaz(e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_karte_hasla(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Zmiana hasła",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        self._etykieta_pola(wewnatrz, "Obecne hasło")
        self._pole_stare = ctk.CTkEntry(wewnatrz, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_stare.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Nowe hasło")
        self._pole_nowe = ctk.CTkEntry(wewnatrz, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_nowe.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Powtórz nowe hasło")
        self._pole_powtorz = ctk.CTkEntry(wewnatrz, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_powtorz.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk = ctk.CTkButton(
            wewnatrz,
            text="Zmień hasło",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zmien_haslo,
        )
        self._przycisk.pack(fill="x")

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

    def odswiez(self) -> None:
        self._odswiez_stan_backupu()

    def _zmien_haslo(self) -> None:
        stare = self._pole_stare.get()
        nowe = self._pole_nowe.get()
        powtorz = self._pole_powtorz.get()

        if not stare:
            komunikat_bledu(self, "Podaj obecne hasło.")
            return
        if len(nowe) < 4:
            komunikat_bledu(self, "Nowe hasło musi mieć co najmniej 4 znaki.")
            return
        if nowe != powtorz:
            komunikat_bledu(self, "Nowe hasła nie są identyczne.")
            return

        self._przycisk.configure(state="disabled")

        def zadanie() -> bool:
            if not auth.zweryfikuj_haslo(stare):
                return False
            auth.ustaw_haslo(nowe)
            return True

        def sukces(udane: bool) -> None:
            self._przycisk.configure(state="normal")
            if udane:
                self._pole_stare.delete(0, "end")
                self._pole_nowe.delete(0, "end")
                self._pole_powtorz.delete(0, "end")
                komunikat_info(self, "Hasło zostało zmienione.")
            else:
                komunikat_bledu(self, "Nieprawidłowe obecne hasło.")

        def blad(e) -> None:
            self._przycisk.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_karte_o_aplikacji(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="O aplikacji",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        ctk.CTkLabel(
            wewnatrz,
            text=f"Faktury Pro w wersji {WERSJA}",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        # Baner dostepnosci nowszej wersji - CELOWO trwaly (nie znikajacy
        # sam, w odroznieniu od pokaz_toast ponizej), zeby link do pobrania
        # zostal widoczny, dopoki uzytkownik sam nie zamknie karty Ustawien.
        # Ukryty domyslnie - pokazywany tylko po sprawdzeniu, ktore faktycznie
        # znajdzie nowsza wersje.
        self._baner_aktualizacji = ctk.CTkFrame(
            wewnatrz, fg_color=styl.KOLOR_OSTRZEZENIE_TLO, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self._etykieta_baneru_aktualizacji = ctk.CTkLabel(
            self._baner_aktualizacji,
            text="",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_OSTRZEZENIE,
            anchor="w",
            justify="left",
            wraplength=260,
        )
        self._etykieta_baneru_aktualizacji.pack(
            padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_MALY, 0), fill="x"
        )
        ctk.CTkButton(
            self._baner_aktualizacji,
            text="Pobierz nową wersję",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OSTRZEZENIE,
            text_color=styl.KOLOR_OSTRZEZENIE,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=lambda: webbrowser.open(self._url_pobierania_aktualizacji),
        ).pack(padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY, fill="x")
        self._url_pobierania_aktualizacji = ""
        # Nie .pack() tutaj - dopiero _pokaz_baner_aktualizacji() go pokazuje.

        self._przycisk_sprawdz_aktualizacje = ctk.CTkButton(
            wewnatrz,
            text="Sprawdź aktualizacje",
            font=styl.CZCIONKA_TRESC,
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._sprawdz_aktualizacje,
        )
        self._przycisk_sprawdz_aktualizacje.pack(fill="x")

    def _pokaz_baner_aktualizacji(self, wersja_najnowsza: str, url_pobierania: str) -> None:
        self._url_pobierania_aktualizacji = url_pobierania
        self._etykieta_baneru_aktualizacji.configure(
            text=f"Dostępna nowsza wersja {wersja_najnowsza}."
        )
        self._baner_aktualizacji.pack(
            fill="x", pady=(0, styl.ODSTEP_SREDNI), before=self._przycisk_sprawdz_aktualizacje
        )

    def _sprawdz_aktualizacje(self) -> None:
        ustaw_tekst_ladowania(
            self._przycisk_sprawdz_aktualizacje, True, "Sprawdź aktualizacje", "Sprawdzanie..."
        )

        def zadanie():
            return api_client.sprawdz_aktualizacje()

        def sukces(wynik: dict) -> None:
            ustaw_tekst_ladowania(self._przycisk_sprawdz_aktualizacje, False, "Sprawdź aktualizacje")
            if wynik["dostepna_nowsza_wersja"]:
                self._pokaz_baner_aktualizacji(wynik["wersja_najnowsza"], wynik["url_pobierania"])
            else:
                pokaz_toast(self, "Masz najnowszą wersję aplikacji.", typ="sukces")

        def blad(e) -> None:
            ustaw_tekst_ladowania(self._przycisk_sprawdz_aktualizacje, False, "Sprawdź aktualizacje")
            pokaz_toast(self, "Nie udało się sprawdzić dostępności aktualizacji.", typ="ostrzezenie")

        uruchom_w_tle(self, zadanie, sukces, blad)

    # -- pakiet diagnostyczny na potrzeby wsparcia zdalnego (Faza 26) - dla
    # uzytkownika nietechnicznego, ktory nie potrafi opisac bledu ani znalezc
    # pliku logow samodzielnie. Appka NIC nie wysyla sama - tylko przygotowuje
    # plik ZIP na Pulpicie (patrz gui/diagnostyka.py po pelne uzasadnienie,
    # w tym co CELOWO nie trafia do pakietu). ----------------------------

    def _zbuduj_karte_diagnostyki(self, master) -> None:
        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(pady=(0, styl.ODSTEP_SREDNI), fill="x")

        ctk.CTkLabel(
            karta,
            text="Zgłoś problem",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        opis = (
            "Jeśli coś w aplikacji nie działa, przygotuj pakiet diagnostyczny "
            "i wyślij go mailem na adres wsparcia razem z krótkim opisem "
            "problemu. Aplikacja NIC nie wysyła sama przez internet - tylko "
            "zapisuje plik na Twoim Pulpicie, resztę robisz Ty."
        )
        profil_id = profil.id_profilu_aktywnego()
        if profil_id is not None:
            wpis_profilu = profile_rejestr.pobierz(profil_id)
            nazwa_profilu = wpis_profilu.nazwa_wyswietlana if wpis_profilu else None
            opis += (
                f"\n\nPakiet będzie dotyczył BIEŻĄCO otwartej firmy: "
                f"„{nazwa_profilu or 'nieskonfigurowana'}”."
            )

        ctk.CTkLabel(
            wewnatrz,
            text=opis,
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=320,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk_diagnostyka = ctk.CTkButton(
            wewnatrz,
            text="Przygotuj pakiet diagnostyczny",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._utworz_pakiet_diagnostyczny,
        )
        self._przycisk_diagnostyka.pack(fill="x")

    def _utworz_pakiet_diagnostyczny(self) -> None:
        ustaw_tekst_ladowania(
            self._przycisk_diagnostyka, True, "Przygotuj pakiet diagnostyczny", "Przygotowywanie..."
        )

        def zadanie():
            return diagnostyka.utworz_pakiet_diagnostyczny()

        def sukces(plik: Path) -> None:
            ustaw_tekst_ladowania(self._przycisk_diagnostyka, False, "Przygotuj pakiet diagnostyczny")
            otworzyc = messagebox.askyesno(
                "Pakiet diagnostyczny gotowy",
                f"Plik zapisany na Pulpicie jako:\n„{plik.name}”.\n\n"
                f"Wyślij go mailem na {diagnostyka.ADRES_WSPARCIA}, opisując "
                "krótko, co się dzieje.\n\n"
                "Czy otworzyć folder z tym plikiem?",
                parent=self,
            )
            if otworzyc:
                os.startfile(plik.parent)

        def blad(e) -> None:
            ustaw_tekst_ladowania(self._przycisk_diagnostyka, False, "Przygotuj pakiet diagnostyczny")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    # -- usuwanie profilu firmy (Faza 25) - NIEODWRACALNE: kasuje baze danych,
    # katalog danych i wpis w rejestrze tego jednego profilu. Inne profile na
    # tym komputerze pozostaja calkowicie nienaruszone. Ukryta w trybie
    # deweloperskim (profil.id_profilu_aktywnego() is None), bo tam nie ma
    # zadnego "profilu" do usuniecia. ------------------------------------

    def _zbuduj_karte_usuwania_profilu(self, master) -> None:
        if profil.id_profilu_aktywnego() is None:
            return

        karta = ctk.CTkFrame(
            master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.pack(fill="x")

        ctk.CTkLabel(
            karta,
            text="Usuń tę firmę",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        ostrzezenie = ctk.CTkFrame(
            wewnatrz, fg_color=styl.KOLOR_BLAD_TLO, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        ostrzezenie.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))
        ctk.CTkLabel(
            ostrzezenie,
            text=(
                "Usunięcie firmy jest NIEODWRACALNE - kasuje jej bazę danych, "
                "ustawienia, logo i dane KSeF zapisane na tym komputerze. Inne "
                "firmy skonfigurowane w Faktury Pro NIE są naruszane."
            ),
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_BLAD,
            wraplength=280,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_SREDNI)

        self._etykieta_pola(wewnatrz, "Wpisz dokładną nazwę firmy, aby potwierdzić")
        self._pole_potwierdzenia_usuniecia = ctk.CTkEntry(wewnatrz, font=styl.CZCIONKA_TRESC)
        self._pole_potwierdzenia_usuniecia.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        self._pole_potwierdzenia_usuniecia.bind(
            "<KeyRelease>", self._na_zmiane_potwierdzenia_usuniecia
        )

        self._przycisk_usun_profil = ctk.CTkButton(
            wewnatrz,
            text="Usuń tę firmę z listy profili",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_BLAD,
            text_color=styl.KOLOR_BLAD,
            hover_color=styl.KOLOR_BLAD_TLO,
            state="disabled",
            command=self._usun_profil,
        )
        self._przycisk_usun_profil.pack(fill="x")

    def _na_zmiane_potwierdzenia_usuniecia(self, _zdarzenie=None) -> None:
        nazwa_oczekiwana = self._pola_firmy["nazwa"].get().strip()
        wpisana = self._pole_potwierdzenia_usuniecia.get().strip()
        aktywny = bool(nazwa_oczekiwana) and wpisana == nazwa_oczekiwana
        self._przycisk_usun_profil.configure(state="normal" if aktywny else "disabled")

    def _usun_profil(self) -> None:
        if not messagebox.askyesno(
            "Usunięcie firmy",
            "Zamierzasz TRWALE usunąć tę firmę: jej bazę danych, ustawienia, "
            "logo i dane KSeF zapisane na tym komputerze zostaną skasowane. "
            "Tej operacji nie można cofnąć.\n\n"
            "Czy na pewno chcesz kontynuować?",
            icon="warning",
            parent=self,
        ):
            return

        profil_id = profil.id_profilu_aktywnego()
        wpis_profilu = profile_rejestr.pobierz(profil_id)
        if wpis_profilu is None:
            komunikat_bledu(self, "Nie udało się odnaleźć tego profilu w rejestrze.")
            return

        self._przycisk_usun_profil.configure(state="disabled")

        def zadanie():
            from gui import proces_aplikacji

            proces_aplikacji.zatrzymaj_serwer_fastapi()

            from gui.postgres_serwer import usun_baze

            usun_baze(wpis_profilu.nazwa_bazy)
            shutil.rmtree(profil.katalog_profilu(profil_id), ignore_errors=True)
            profile_rejestr.usun(profil_id)

        def sukces(_wynik) -> None:
            messagebox.showinfo(
                "Firma usunięta",
                "Firma została usunięta z listy profili. Aplikacja zostanie "
                "teraz zamknięta.",
                parent=self,
            )
            from gui import proces_aplikacji

            # zatrzymaj_wszystko() zatrzymuje TAKZE prywatny Postgres (nie
            # tylko watek FastAPI, ktory `zadanie()` juz zatrzymal wyzej, zeby
            # DROP DATABASE mial sie do czego polaczyc) - bez tego wywolania
            # proces postgres.exe zostawalby osierocony po os._exit() ponizej,
            # dokladnie ten sam problem co installer.iss musial juz raz
            # naprawiac dla awaryjnego zamkniecia appki (patrz CLAUDE.md,
            # Faza 18C). Ten sam wzorzec co
            # gui/windows/dialog_kopii_zapasowej.py:DialogPrzywrocBackup po
            # udanym przywroceniu backupu.
            proces_aplikacji.zatrzymaj_wszystko()
            os._exit(0)

        def blad(e) -> None:
            self._przycisk_usun_profil.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
