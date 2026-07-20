"""Kreator importu danych z pliku CSV (Faza 26) - wspolna baza dla dialog_
importu_klientow.py i dialog_importu_produktow.py (mechanika obu jest
analogiczna: wybor pliku -> mapowanie kolumn -> podglad z walidacja ->
import -> podsumowanie; roznia sie tylko polami modelu i regulami
walidacji/duplikatow, wiec te roznice wchodza przez metody nadpisywane w
podklasach zamiast kopiowania calego kreatora).

Priorytet (patrz CLAUDE.md i notatka do Fazy 26): uzytkownik ZAWSZE widzi
podglad z jasno oznaczonymi wierszami, ktore nie przejda walidacji, PRZED
kliknieciem "Importuj", i pelne podsumowanie po - nigdy cichy czesciowy
import. Krok podgladu wykonuje "suchy" (bez zapisu) przebieg DOKLADNIE tej
samej walidacji co finalny import (patrz app/services/klienci.py:
importuj_klientow, zapisz=False) - w tym wykrywanie duplikatow wzgledem
CALEJ bazy, nie tylko tego, co GUI ma akurat w pamieci podrecznej.
"""

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from gui import api_client, styl
from gui.import_csv import BladOdczytuCsv, auto_dopasuj_kolumny, wczytaj_csv
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.tabela import Tabela

_POMIN = "— pomiń —"
_LIMIT_PODGLADU = 30


class DialogImportuCsv(OknoFormularza):
    # -- do nadpisania w podklasach --------------------------------

    #: (klucz_pola, etykieta, wymagane, aliasy_naglowkow_do_auto_dopasowania)
    KOLUMNY_PODGLADU: list[str] = []

    def pola(self) -> list[tuple[str, str, bool, tuple[str, ...]]]:
        raise NotImplementedError

    def koerencja_wiersza(self, surowe: dict[str, str]) -> tuple[dict | None, str | None]:
        """Przeksztalca surowy tekst z jednego wiersza CSV (klucz_pola -> tekst,
        pusty string gdy kolumna niezmapowana albo komorka pusta) na gotowe dane
        (dict do wyslania do API) - zwraca (dane, None) albo (None, powod_bledu).
        Odpowiada WYLACZNIE za parsowanie formatu (liczby, typy) - reguly
        biznesowe (wymagane pola z ksztaltu KlientCreate/ProduktCreate, duplikaty)
        sa juz zweryfikowane docelowo w backendzie (patrz modul docstring)."""
        raise NotImplementedError

    def zbuduj_dodatkowe_opcje_mapowania(self, master) -> None:
        pass

    def wywolaj_podglad(self, wiersze: list[dict]) -> list[dict]:
        raise NotImplementedError

    def wywolaj_import(self, wiersze: list[dict]) -> list[dict]:
        raise NotImplementedError

    def formatery_podgladu(self) -> dict[str, Callable[[dict], str]]:
        return {}

    # -- konstrukcja --------------------------------

    def __init__(self, master, tytul: str, on_zaimportowano: Callable[[], None]):
        super().__init__(master)
        self.title(tytul)
        self.geometry("780x680")
        self._on_zaimportowano = on_zaimportowano

        self._sciezka_pliku: str | None = None
        self._naglowki: list[str] = []
        self._wiersze_surowe: list[list[str]] = []
        self._mapowanie: dict[str, str | None] = {}
        self._wyniki_walidacji: list[dict] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._tresc = ctk.CTkFrame(self, fg_color="transparent")
        self._tresc.grid(
            row=0, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0)
        )
        self._pasek_przyciskow = ctk.CTkFrame(self, fg_color="transparent")
        self._pasek_przyciskow.grid(
            row=1, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        self._pokaz_krok_wyboru_pliku()

    def _wyczysc(self) -> None:
        for dziecko in self._tresc.winfo_children():
            dziecko.destroy()
        for dziecko in self._pasek_przyciskow.winfo_children():
            dziecko.destroy()

    def _dodaj_przycisk_wstecz(self, komenda: Callable[[], None]) -> ctk.CTkButton:
        przycisk = ctk.CTkButton(
            self._pasek_przyciskow,
            text="Wstecz",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=komenda,
        )
        przycisk.pack(side="left")
        return przycisk

    def _dodaj_przycisk_glowny(
        self, tekst: str, komenda: Callable[[], None], stan: str = "normal"
    ) -> ctk.CTkButton:
        przycisk = ctk.CTkButton(
            self._pasek_przyciskow,
            text=tekst,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=komenda,
            state=stan,
        )
        przycisk.pack(side="right")
        return przycisk

    # -- krok 1: wybor pliku --------------------------------

    def _pokaz_krok_wyboru_pliku(self) -> None:
        self._wyczysc()

        ctk.CTkLabel(
            self._tresc,
            text="Wybierz plik CSV z danymi do zaimportowania. W kolejnym kroku "
            "przypiszesz kolumny pliku do pól aplikacji - układ pliku może być "
            "dowolny.",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=700,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._banner_plik = Banner(self._tresc)
        self._banner_plik.ustaw_geometrie(
            lambda: self._banner_plik.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))
        )

        ctk.CTkButton(
            self._tresc,
            text="Wybierz plik CSV...",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._wybierz_plik,
        ).pack(anchor="w")

        ctk.CTkButton(
            self._pasek_przyciskow,
            text="Anuluj",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self._zamknij_z_potwierdzeniem,
        ).pack(side="right")

    def _wybierz_plik(self) -> None:
        from tkinter import filedialog

        sciezka = filedialog.askopenfilename(
            parent=self, title="Wybierz plik CSV", filetypes=[("Plik CSV", "*.csv")]
        )
        if not sciezka:
            return
        try:
            naglowki, wiersze = wczytaj_csv(sciezka)
        except BladOdczytuCsv as e:
            self._banner_plik.pokaz(str(e))
            return

        self._sciezka_pliku = sciezka
        self._naglowki = naglowki
        self._wiersze_surowe = wiersze
        self._mapowanie = {}
        self._pokaz_krok_mapowania()

    # -- krok 2: mapowanie kolumn --------------------------------

    def _pokaz_krok_mapowania(self) -> None:
        self._wyczysc()

        ctk.CTkLabel(
            self._tresc,
            text=f"Plik: {Path(self._sciezka_pliku).name}  •  {len(self._wiersze_surowe)} wierszy danych",
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._banner_mapowanie = Banner(self._tresc)
        self._banner_mapowanie.ustaw_geometrie(
            lambda: self._banner_mapowanie.pack(fill="x", pady=(0, styl.ODSTEP_MALY))
        )

        przewijany = ctk.CTkScrollableFrame(self._tresc, fg_color="transparent")
        przewijany.pack(fill="both", expand=True)
        przewijany.grid_columnconfigure(0, weight=1)
        przewijany.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            przewijany,
            text="Dopasuj kolumny pliku do pól aplikacji:",
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, styl.ODSTEP_MALY))

        pola = self.pola()
        auto = auto_dopasuj_kolumny(pola, self._naglowki)
        opcje = [_POMIN] + self._naglowki

        self._zmienne_mapowania: dict[str, ctk.StringVar] = {}
        for indeks, (klucz, etykieta, _wymagane, _aliasy) in enumerate(pola, start=1):
            ctk.CTkLabel(
                przewijany,
                text=etykieta,
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
            ).grid(row=indeks, column=0, sticky="w", padx=(0, styl.ODSTEP_SREDNI), pady=(0, styl.ODSTEP_MALY))

            zmienna = ctk.StringVar(value=auto.get(klucz, _POMIN))
            ctk.CTkOptionMenu(
                przewijany,
                values=opcje,
                variable=zmienna,
                fg_color=styl.KOLOR_AKCENT,
                button_color=styl.KOLOR_AKCENT,
                button_hover_color=styl.KOLOR_AKCENT_HOVER,
            ).grid(row=indeks, column=1, sticky="ew", pady=(0, styl.ODSTEP_MALY))
            self._zmienne_mapowania[klucz] = zmienna

        self.zbuduj_dodatkowe_opcje_mapowania(przewijany)

        self._dodaj_przycisk_wstecz(self._pokaz_krok_wyboru_pliku)
        self._dodaj_przycisk_glowny("Dalej", self._zatwierdz_mapowanie)

    def _zatwierdz_mapowanie(self) -> None:
        self._mapowanie = {
            klucz: (zmienna.get() if zmienna.get() != _POMIN else None)
            for klucz, zmienna in self._zmienne_mapowania.items()
        }
        brakujace = [
            etykieta.rstrip(" *")
            for klucz, etykieta, wymagane, _aliasy in self.pola()
            if wymagane and not self._mapowanie.get(klucz)
        ]
        if brakujace:
            self._banner_mapowanie.pokaz("Zmapuj wymagane pola: " + ", ".join(brakujace))
            return
        self._pokaz_krok_podgladu()

    # -- krok 3: podglad (walidacja lokalna + "sucha" walidacja serwera) -----

    def _wykonaj_koerencje_lokalna(self) -> None:
        indeksy = {
            klucz: (self._naglowki.index(naglowek) if naglowek else None)
            for klucz, naglowek in self._mapowanie.items()
        }
        self._wyniki_walidacji = []
        for numer_wiersza, wiersz_surowy in enumerate(self._wiersze_surowe, start=2):
            surowe: dict[str, str] = {}
            for klucz, indeks in indeksy.items():
                if indeks is not None and indeks < len(wiersz_surowy):
                    surowe[klucz] = wiersz_surowy[indeks].strip()
                else:
                    surowe[klucz] = ""
            dane, blad = self.koerencja_wiersza(surowe)
            self._wyniki_walidacji.append(
                {"numer_wiersza": numer_wiersza, "surowe": surowe, "dane": dane, "blad": blad}
            )

    def _kolumny_podgladu(self) -> list[tuple[str, str, int]]:
        etykiety = {klucz: etykieta.rstrip(" *") for klucz, etykieta, _w, _a in self.pola()}
        kolumny = [("numer_wiersza", "Wiersz", 1)]
        kolumny += [(k, etykiety.get(k, k), 2) for k in self.KOLUMNY_PODGLADU]
        kolumny += [("status", "Status", 1), ("uwagi", "Uwagi", 3)]
        return kolumny

    def _wiersz_do_tabeli(self, wpis: dict) -> dict:
        podglad = dict(wpis["surowe"])
        if wpis["dane"]:
            podglad.update({k: v for k, v in wpis["dane"].items() if k in self.KOLUMNY_PODGLADU})
        wynik = {"numer_wiersza": wpis["numer_wiersza"]}
        wynik.update({k: podglad.get(k, "") for k in self.KOLUMNY_PODGLADU})
        wynik["status"] = "Błąd" if wpis["blad"] else "OK"
        wynik["uwagi"] = wpis["blad"] or ""
        return wynik

    def _pokaz_krok_podgladu(self) -> None:
        self._wykonaj_koerencje_lokalna()
        self._wyczysc()

        self._etykieta_podsumowania = ctk.CTkLabel(
            self._tresc,
            text="Sprawdzanie danych...",
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        )
        self._etykieta_podsumowania.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._tabela_podgladu = Tabela(self._tresc, kolumny=self._kolumny_podgladu())
        self._tabela_podgladu.pack(fill="both", expand=True)
        self._tabela_podgladu.pokaz_ladowanie()

        self._etykieta_obciecia = ctk.CTkLabel(
            self._tresc, text="", font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_obciecia.pack(fill="x", pady=(styl.ODSTEP_MIKRO, 0))

        self._dodaj_przycisk_wstecz(self._pokaz_krok_mapowania)
        self._przycisk_importuj = self._dodaj_przycisk_glowny(
            "Importuj", self._importuj, stan="disabled"
        )

        wiersze_do_sprawdzenia = [w for w in self._wyniki_walidacji if w["blad"] is None]
        if not wiersze_do_sprawdzenia:
            self._po_podgladzie_serwera([])
            return

        def zadanie():
            return self.wywolaj_podglad(
                [
                    {**w["dane"], "numer_wiersza": w["numer_wiersza"]}
                    for w in wiersze_do_sprawdzenia
                ]
            )

        def sukces(wyniki_serwera: list[dict]) -> None:
            self._po_podgladzie_serwera(wyniki_serwera)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            self._pokaz_krok_mapowania()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _po_podgladzie_serwera(self, wyniki_serwera: list[dict]) -> None:
        bledy_serwera = {
            w["numer_wiersza"]: w["komunikat"] for w in wyniki_serwera if not w["sukces"]
        }
        for wpis in self._wyniki_walidacji:
            if wpis["blad"] is None and wpis["numer_wiersza"] in bledy_serwera:
                wpis["blad"] = bledy_serwera[wpis["numer_wiersza"]]

        liczba_ok = sum(1 for w in self._wyniki_walidacji if w["blad"] is None)
        liczba_bledow = len(self._wyniki_walidacji) - liczba_ok
        self._etykieta_podsumowania.configure(
            text=(
                f"{len(self._wyniki_walidacji)} wierszy w pliku: {liczba_ok} gotowych do "
                f"importu, {liczba_bledow} pominiętych z powodu błędów."
            )
        )

        wiersze_do_pokazania = self._wyniki_walidacji[:_LIMIT_PODGLADU]
        wiersze_tabeli = [self._wiersz_do_tabeli(w) for w in wiersze_do_pokazania]
        kolory = {
            "status": lambda w: styl.KOLOR_BLAD if w["status"] == "Błąd" else styl.KOLOR_SUKCES,
            "uwagi": lambda w: styl.KOLOR_BLAD if w["status"] == "Błąd" else styl.KOLOR_TEKST_DRUGORZEDNY,
        }
        self._tabela_podgladu.ustaw_dane(
            wiersze_tabeli, formatery=self.formatery_podgladu(), kolory=kolory
        )

        if len(self._wyniki_walidacji) > _LIMIT_PODGLADU:
            self._etykieta_obciecia.configure(
                text=f"Pokazano pierwsze {_LIMIT_PODGLADU} z {len(self._wyniki_walidacji)} wierszy."
            )

        self._przycisk_importuj.configure(
            text=f"Importuj ({liczba_ok})", state="normal" if liczba_ok else "disabled"
        )

    # -- krok 4: import + podsumowanie --------------------------------

    def _importuj(self) -> None:
        wiersze_ok = [w for w in self._wyniki_walidacji if w["blad"] is None]
        ustaw_tekst_ladowania(
            self._przycisk_importuj, True, f"Importuj ({len(wiersze_ok)})", "Importowanie..."
        )
        for dziecko in self._pasek_przyciskow.winfo_children():
            if dziecko is not self._przycisk_importuj:
                dziecko.configure(state="disabled")

        def zadanie():
            return self.wywolaj_import(
                [{**w["dane"], "numer_wiersza": w["numer_wiersza"]} for w in wiersze_ok]
            )

        def sukces(wyniki_serwera: list[dict]) -> None:
            self._pokaz_podsumowanie(wyniki_serwera)

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_importuj, False, f"Importuj ({len(wiersze_ok)})")
            for dziecko in self._pasek_przyciskow.winfo_children():
                dziecko.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _pokaz_podsumowanie(self, wyniki_serwera: list[dict]) -> None:
        self._wyczysc()

        sukcesy = sum(1 for w in wyniki_serwera if w["sukces"])
        niepowodzenia_serwera = [w for w in wyniki_serwera if not w["sukces"]]
        pominiete_lokalnie = [w for w in self._wyniki_walidacji if w["blad"] is not None]
        laczna_liczba_pominietych = len(pominiete_lokalnie) + len(niepowodzenia_serwera)

        ctk.CTkLabel(
            self._tresc,
            text=f"Zaimportowano {sukcesy} z {len(self._wyniki_walidacji)} wierszy.",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        if laczna_liczba_pominietych:
            ctk.CTkLabel(
                self._tresc,
                text=f"Pominięto {laczna_liczba_pominietych} wierszy:",
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
            ).pack(fill="x", pady=(0, styl.ODSTEP_MALY))

            lista = ctk.CTkScrollableFrame(
                self._tresc, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
            )
            lista.pack(fill="both", expand=True, pady=(0, styl.ODSTEP_MALY))

            powody = {w["numer_wiersza"]: w["blad"] for w in pominiete_lokalnie}
            powody.update({w["numer_wiersza"]: w["komunikat"] for w in niepowodzenia_serwera})
            for numer_wiersza in sorted(powody):
                ctk.CTkLabel(
                    lista,
                    text=f"Wiersz {numer_wiersza}: {powody[numer_wiersza]}",
                    font=styl.CZCIONKA_DROBNA,
                    text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                    wraplength=700,
                    justify="left",
                    anchor="w",
                ).pack(fill="x", pady=styl.ODSTEP_MIKRO, padx=styl.ODSTEP_MALY)

        ctk.CTkButton(
            self._pasek_przyciskow,
            text="Zamknij",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=lambda: self._zakoncz(sukcesy),
        ).pack(side="right")

    def _zakoncz(self, sukcesy: int) -> None:
        master = self.master
        self._on_zaimportowano()
        self.destroy()
        if sukcesy:
            pokaz_toast(master, f"Zaimportowano {sukcesy} wierszy.")
