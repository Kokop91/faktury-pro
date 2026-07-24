import logging
import re

import customtkinter as ctk

from gui import api_client, ikony, nastawienia, styl
from gui.ikona_okna import ustaw_ikone
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_ostrzezenie, pokaz_toast
from gui.windows.widok_dashboard import WidokDashboard
from gui.windows.widok_dokumentow_kosztowych import WidokDokumentowKosztowych
from gui.windows.widok_faktur import WidokFaktur
from gui.windows.widok_faktur_cyklicznych import WidokFakturCyklicznych
from gui.windows.widok_klientow import WidokKlientow
from gui.windows.widok_magazynu import WidokMagazynu
from gui.windows.widok_naleznosci import WidokNaleznosci
from gui.windows.widok_ofert import WidokOfert
from gui.windows.widok_rentownosci import WidokRentownosci
from gui.windows.widok_ustawien import WidokUstawien

_KLUCZ_GEOMETRII = "geometria_okna_glownego"
_WZORZEC_GEOMETRII = re.compile(r"^\d+x\d+\+-?\d+\+-?\d+$")

# Sprawdzenia przy starcie (ponizej) sa CELOWO ciche wobec uzytkownika -
# appka nie ma pokazywac okna z bledem przy KAZDYM uruchomieniu tylko dlatego,
# ze np. KSeF akurat ma przerwe techniczna. "Cichy" nie powinien jednak
# znaczyc "bez sladu" (patrz przeglad odpornosci appki na problemy sieciowe) -
# logujemy, zeby awaria byla mozliwa do zdiagnozowania (plik logu, patrz
# gui/main.py:_skonfiguruj_logowanie), zamiast znikac bez sladu.
_log = logging.getLogger(__name__)


class GlowneOkno(ctk.CTk):
    def __init__(self):
        super().__init__()
        ustaw_ikone(self)
        self.title("Faktury Pro")
        self.geometry("1150x720")
        self.minsize(900, 600)
        self.configure(fg_color=styl.KOLOR_TLO)
        self._przywroc_geometrie()

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._pasek_boczny = _PasekBoczny(self, on_nawigacja=self._pokaz_widok)
        self._pasek_boczny.grid(row=0, column=0, sticky="nsw")

        self._kontener = ctk.CTkFrame(self, fg_color=styl.KOLOR_TLO, corner_radius=0)
        self._kontener.grid(row=0, column=1, sticky="nsew")
        self._kontener.grid_columnconfigure(0, weight=1)
        self._kontener.grid_rowconfigure(0, weight=1)

        self._widoki: dict[str, ctk.CTkFrame] = {}
        self._widok_aktywny: str | None = None

        self._pokaz_widok("dashboard")
        self._zarejestruj_skroty()
        # Opoznione o chwile (po starcie mainloop) - Faza 15, KLUCZOWY mechanizm
        # "sprawdz przy starcie" zamiast systemowego harmonogramu (appka
        # desktopowa nie dziala 24/7). Nigdy nie generuje nic samo - tylko
        # informuje i czeka na decyzje uzytkownika, patrz DialogZaleglychCyklicznych.
        self.after(300, self._sprawdz_faktury_cykliczne)
        # Faza 12C: sprawdzenie KSeF (siec + uwierzytelnienie) jest OPCJONALNE
        # i wylacznie na zyczenie uzytkownika (ustawienie w Ustawieniach) -
        # w odroznieniu od odznaki liczby nowych dokumentow ponizej, ktora jest
        # czysto lokalnym zapytaniem do bazy i odswieza sie zawsze.
        self.after(400, self._sprawdz_koszty_ksef_jesli_wlaczone)
        # Faza 22 - ten sam wzorzec "sprawdz przy starcie, nigdy nie wymuszaj"
        # co faktury cykliczne powyzej. Czysto lokalny odczyt pliku
        # (gui/kopia_zapasowa.py), wiec bez uruchom_w_tle/opoznienia sieciowego.
        self.after(500, self._sprawdz_backup)
        # Faza 23 - identyczny wzorzec "sprawdz przy starcie, nigdy nie
        # wymuszaj" co faktury cykliczne (Faza 15).
        self.after(600, self._sprawdz_przypomnienia_platnosci)

    def _sprawdz_faktury_cykliczne(self) -> None:
        def zadanie():
            return api_client.pobierz_zalegle_faktury_cykliczne()

        def sukces(zalegle: list[dict]) -> None:
            if not zalegle:
                return
            from gui.windows.dialog_zaleglych_cyklicznych import DialogZaleglychCyklicznych

            DialogZaleglychCyklicznych(
                self, zalegle, on_wygenerowano=self._po_wygenerowaniu_cyklicznych
            )

        def blad(e) -> None:
            # Cichy brak powiadomienia startowego nie powinien przeszkadzac w
            # pracy, ale zalogowane - patrz komentarz przy _log powyzej.
            _log.warning("Sprawdzenie zaleglych faktur cyklicznych przy starcie nie powiodlo sie: %s", e)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _sprawdz_koszty_ksef_jesli_wlaczone(self) -> None:
        def zadanie():
            ustawienia = api_client.pobierz_ustawienia_ksef()
            if not ustawienia.get("sprawdzaj_koszty_przy_starcie"):
                return None
            return api_client.pobierz_nowe_koszty_ksef()

        def sukces(wynik: dict | None) -> None:
            if wynik is None:
                return
            self._odswiez_odznake_kosztow()
            if wynik.get("liczba_nowych"):
                widok = self._widoki.get("koszty")
                odswiez = getattr(widok, "odswiez", None) if widok is not None else None
                if callable(odswiez):
                    odswiez()

        def blad(e) -> None:
            # Ten check FAKTYCZNIE dotyka sieci (zapytanie do KSeF) - tu
            # zalogowanie ma najwieksze znaczenie z calej czwórki (np.
            # wygasly/nieprawidlowy token, przerwa techniczna KSeF).
            _log.warning("Sprawdzenie nowych kosztow KSeF przy starcie nie powiodlo sie: %s", e)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _sprawdz_backup(self) -> None:
        from gui import kopia_zapasowa as kz

        stan = kz.stan_backupu()
        if not stan["przeterminowany"]:
            return

        if stan["gotowy_do_automatycznego_wykonania"]:
            self._wykonaj_backup_automatyczny()
            return

        from gui.windows.dialog_przypomnienia_backupu import DialogPrzypomnieniaBackupu

        DialogPrzypomnieniaBackupu(
            self,
            nigdy_skonfigurowano=stan["katalog_docelowy"] is None,
            dni_od_ostatniego=stan["dni_od_ostatniego"],
            on_przejdz=lambda: self._pokaz_widok("ustawienia"),
        )

    def _wykonaj_backup_automatyczny(self) -> None:
        """Tryb 'Wykonuj automatycznie' (rozszerzenie Fazy 22) - w
        odroznieniu od DialogPrzypomnieniaBackupu powyzej appka NIE pyta,
        tylko sama wykonuje kopie w tle, bez zadnego widocznego okna
        modalnego. Sukces: krotki, nieinwazyjny toast (ten sam mechanizm co
        reszta appki). Niepowodzenie: CELOWO NIE cichy jak inne sprawdzenia
        startowe w tym pliku - uzytkownik musi sie dowiedziec, ze jego dane
        NIE sa zabezpieczone, wiec nieblokujace ale WIDOCZNE ostrzezenie
        (messagebox), nie tylko wpis w logu."""
        from gui import kopia_zapasowa as kz
        from gui.api_client import ApiError

        def zadanie():
            try:
                return kz.wykonaj_backup_automatyczny()
            except kz.BladKopiiZapasowej as e:
                raise ApiError(str(e)) from e

        def sukces(_plik) -> None:
            pokaz_toast(self, "Kopia zapasowa wykonana pomyślnie.", typ="sukces")

        def blad(e: ApiError) -> None:
            _log.warning("Automatyczna kopia zapasowa nie powiodla sie: %s", e.komunikat)
            komunikat_ostrzezenie(
                self,
                "Automatyczna kopia zapasowa nie powiodła się:\n\n"
                f"{e.komunikat}\n\n"
                "Sprawdź lokalizację docelową w Ustawieniach (np. czy dysk "
                "sieciowy/USB jest podłączony) i spróbuj ponownie ręcznie.",
                tytul="Kopia zapasowa nie powiodła się",
            )

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _sprawdz_przypomnienia_platnosci(self) -> None:
        def zadanie():
            return api_client.pobierz_przypomnienia_do_wyslania()

        def sukces(kandydaci: list[dict]) -> None:
            if not kandydaci:
                return
            from gui.windows.dialog_przypomnien_platnosci import DialogPrzypomnienPlatnosci

            DialogPrzypomnienPlatnosci(
                self, kandydaci, on_wyslano=self._po_wyslaniu_przypomnien
            )

        def blad(e) -> None:
            _log.warning("Sprawdzenie przypomnien o platnosciach przy starcie nie powiodlo sie: %s", e)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _po_wyslaniu_przypomnien(self) -> None:
        for klucz in ("faktury", "naleznosci", "dashboard"):
            widok = self._widoki.get(klucz)
            odswiez = getattr(widok, "odswiez", None)
            if callable(odswiez):
                odswiez()

    def _odswiez_odznake_kosztow(self) -> None:
        def zadanie():
            return api_client.liczba_nowych_dokumentow_kosztowych()

        def sukces(liczba: int) -> None:
            self._pasek_boczny.ustaw_odznake("koszty", liczba)

        def blad(e) -> None:
            # Odznaka to tylko wskazowka - brak polaczenia nie powinien
            # przeszkadzac w pracy, ale zalogowane jak reszta checkow wyzej.
            _log.warning("Odswiezenie odznaki liczby nowych dokumentow kosztowych nie powiodlo sie: %s", e)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _po_wygenerowaniu_cyklicznych(self) -> None:
        for klucz in ("cykliczne", "faktury", "dashboard"):
            widok = self._widoki.get(klucz)
            odswiez = getattr(widok, "odswiez", None)
            if callable(odswiez):
                odswiez()

    def _przywroc_geometrie(self) -> None:
        geometria = nastawienia.wczytaj(_KLUCZ_GEOMETRII)
        if isinstance(geometria, str) and _WZORZEC_GEOMETRII.match(geometria):
            self.geometry(geometria)

    def zapisz_geometrie(self) -> None:
        """Wolane z gui/main.py tuz przed zamknieciem aplikacji (Faza 16C:
        zapamietywanie rozmiaru/pozycji okna miedzy sesjami)."""
        nastawienia.zapisz(_KLUCZ_GEOMETRII, self.geometry())

    def _zarejestruj_skroty(self) -> None:
        # bind_all dziala globalnie w calej aplikacji, ALE grab_set() na
        # otwartym formularzu/oknie modalnym (Faza 16C, baza_formularza.py)
        # przechwytuje wszystkie zdarzenia klawiatury dla siebie - te skroty
        # naturalnie nie odpalaja sie, gdy jakies okno modalne jest otwarte.
        self.bind_all("<Control-n>", lambda _z: self._nowa_faktura_globalnie())
        self.bind_all("<F5>", lambda _z: self._odswiez_biezacy_widok())
        self.bind_all("<Control-f>", lambda _z: self._fokus_wyszukiwania())

    def _nowa_faktura_globalnie(self) -> None:
        from gui.windows.formularz_faktury import FormularzFaktury

        widok_faktur = self._widoki.get("faktury")
        on_zapisano = widok_faktur.odswiez if widok_faktur is not None else (lambda: None)
        FormularzFaktury(self, on_zapisano=on_zapisano)

    def _odswiez_biezacy_widok(self) -> None:
        widok = self._widoki.get(self._widok_aktywny) if self._widok_aktywny else None
        odswiez = getattr(widok, "odswiez", None)
        if callable(odswiez):
            odswiez()

    def _fokus_wyszukiwania(self) -> None:
        widok = self._widoki.get(self._widok_aktywny) if self._widok_aktywny else None
        fokus = getattr(widok, "fokus_wyszukiwania", None)
        if callable(fokus):
            fokus()

    def _utworz_widok(self, klucz: str) -> ctk.CTkFrame:
        if klucz == "dashboard":
            return WidokDashboard(self._kontener, on_nawigacja=self._pokaz_widok)
        if klucz == "faktury":
            return WidokFaktur(self._kontener)
        if klucz == "cykliczne":
            return WidokFakturCyklicznych(self._kontener)
        if klucz == "oferty":
            return WidokOfert(self._kontener)
        if klucz == "naleznosci":
            return WidokNaleznosci(self._kontener)
        if klucz == "koszty":
            return WidokDokumentowKosztowych(self._kontener)
        if klucz == "rentownosc":
            return WidokRentownosci(self._kontener)
        if klucz == "klienci":
            return WidokKlientow(self._kontener)
        if klucz == "magazyn":
            return WidokMagazynu(self._kontener)
        if klucz == "ustawienia":
            return WidokUstawien(self._kontener)
        raise ValueError(f"Nieznany widok: {klucz}")

    def _pokaz_widok(self, klucz: str, **parametry) -> None:
        if klucz not in self._widoki:
            widok = self._utworz_widok(klucz)
            widok.grid(row=0, column=0, sticky="nsew")
            self._widoki[klucz] = widok

        widok = self._widoki[klucz]
        widok.tkraise()
        self._pasek_boczny.ustaw_aktywny(klucz)
        self._widok_aktywny = klucz

        # "status_filtr" jest przekazywany TYLKO przez kafelki dashboardu (Faza
        # 16B) - zwykle klikniecie w pasku bocznym nie podaje tego kwarg, wiec
        # nie resetuje filtra, ktory uzytkownik mogl juz recznie ustawic w
        # docelowym widoku (np. w dropdownie statusu na liscie Faktur).
        if "status_filtr" in parametry and hasattr(widok, "ustaw_filtr_status"):
            widok.ustaw_filtr_status(parametry["status_filtr"])

        odswiez = getattr(widok, "odswiez", None)
        if callable(odswiez):
            odswiez()
        self._odswiez_odznake_kosztow()


class _PasekBoczny(ctk.CTkFrame):
    # klucz jest jednoczesnie nazwa ikony w gui/ikony.py.
    POZYCJE = [
        ("dashboard", "Dashboard"),
        ("faktury", "Faktury"),
        ("cykliczne", "Faktury cykliczne"),
        ("oferty", "Oferty"),
        ("naleznosci", "Należności"),
        ("koszty", "Dokumenty kosztowe"),
        ("rentownosc", "Rentowność"),
        ("klienci", "Klienci"),
        ("magazyn", "Magazyn"),
        ("ustawienia", "Ustawienia"),
    ]

    def __init__(self, master, on_nawigacja):
        super().__init__(
            master,
            width=styl.SZEROKOSC_SIDEBAR,
            fg_color=styl.KOLOR_SIDEBAR,
            corner_radius=0,
        )
        self.grid_propagate(False)
        self.on_nawigacja = on_nawigacja
        self._przyciski: dict[str, ctk.CTkButton] = {}
        self._odznaki: dict[str, ctk.CTkLabel] = {}

        tytul = ctk.CTkLabel(
            self,
            text="Faktury Pro",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_SIDEBAR_TEKST,
        )
        tytul.pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY * 2, styl.ODSTEP_DUZY),
            anchor="w",
        )

        for klucz, etykieta in self.POZYCJE:
            przycisk = ctk.CTkButton(
                self,
                text=etykieta,
                image=ikony.ikona_stala(klucz),
                compound="left",
                font=styl.CZCIONKA_TRESC,
                anchor="w",
                corner_radius=styl.PROMIEN_NAROZNIKA,
                fg_color="transparent",
                hover_color=styl.KOLOR_AKCENT_HOVER,
                text_color=styl.KOLOR_SIDEBAR_TEKST,
                command=lambda k=klucz: self.on_nawigacja(k),
            )
            przycisk.pack(
                fill="x", padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_MALY)
            )
            self._przyciski[klucz] = przycisk

    def ustaw_aktywny(self, klucz: str) -> None:
        for klucz_przycisku, przycisk in self._przyciski.items():
            przycisk.configure(
                fg_color=styl.KOLOR_AKCENT
                if klucz_przycisku == klucz
                else "transparent"
            )

    def ustaw_odznake(self, klucz: str, liczba: int) -> None:
        """Male czerwone kolko z liczba w rogu pozycji paska bocznego (Faza
        12C - liczba nowych, nieprzejrzanych dokumentow kosztowych). Ukryte
        calkowicie, gdy liczba <= 0."""
        przycisk = self._przyciski.get(klucz)
        if przycisk is None:
            return
        odznaka = self._odznaki.get(klucz)
        if liczba <= 0:
            if odznaka is not None:
                odznaka.place_forget()
            return
        if odznaka is None:
            odznaka = ctk.CTkLabel(
                przycisk,
                text="",
                font=styl.CZCIONKA_DROBNA,
                text_color="white",
                fg_color=styl.KOLOR_BLAD,
                corner_radius=9,
                width=18,
                height=18,
            )
            self._odznaki[klucz] = odznaka
        odznaka.configure(text=str(liczba) if liczba <= 99 else "99+")
        odznaka.place(relx=1.0, rely=0.5, anchor="e", x=-styl.ODSTEP_MALY)
