import re

import customtkinter as ctk

from gui import api_client, ikony, nastawienia, styl
from gui.watki import uruchom_w_tle
from gui.windows.widok_dashboard import WidokDashboard
from gui.windows.widok_faktur import WidokFaktur
from gui.windows.widok_faktur_cyklicznych import WidokFakturCyklicznych
from gui.windows.widok_klientow import WidokKlientow
from gui.windows.widok_magazynu import WidokMagazynu
from gui.windows.widok_naleznosci import WidokNaleznosci
from gui.windows.widok_ustawien import WidokUstawien

_KLUCZ_GEOMETRII = "geometria_okna_glownego"
_WZORZEC_GEOMETRII = re.compile(r"^\d+x\d+\+-?\d+\+-?\d+$")


class GlowneOkno(ctk.CTk):
    def __init__(self):
        super().__init__()
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

        def blad(_e) -> None:
            pass  # cichy brak powiadomienia startowego nie powinien przeszkadzac w pracy

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
        if klucz == "naleznosci":
            return WidokNaleznosci(self._kontener)
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


class _PasekBoczny(ctk.CTkFrame):
    # klucz jest jednoczesnie nazwa ikony w gui/ikony.py.
    POZYCJE = [
        ("dashboard", "Dashboard"),
        ("faktury", "Faktury"),
        ("cykliczne", "Faktury cykliczne"),
        ("naleznosci", "Należności"),
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
