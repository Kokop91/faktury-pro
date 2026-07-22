from typing import Callable

import customtkinter as ctk
from tkinter import messagebox

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, pokaz_toast, ustaw_tekst_ladowania
from gui.windows.baza_formularza import OknoFormularza
from gui.windows.formularz_dokumentu_magazynowego import FormularzDokumentuMagazynowego
from gui.windows.tabela import Tabela

KOLUMNY_POZYCJI = [
    ("produkt", "Produkt", 3),
    ("ilosc", "Ilość", 1),
    ("cena_zakupu", "Cena zakupu netto", 2),
    ("notatka", "Notatka", 3),
]


class SzczegolyDokumentuMagazynowego(OknoFormularza):
    """Faza 27 - edycja i zatwierdzanie dostepne WYLACZNIE dla dokumentow w
    statusie 'roboczy' (patrz app/services/magazyn_service.py:_wymagaj_roboczego) -
    dla juz zatwierdzonych dokument pozostaje czysto do odczytu, jak przed
    ta faza."""

    def __init__(
        self,
        master,
        dokument_id: int,
        on_zmieniono: Callable[[], None] | None = None,
    ):
        super().__init__(master)
        self.title("Szczegóły dokumentu magazynowego")
        self.geometry("700x640")

        self._dokument_id = dokument_id
        self._on_zmieniono = on_zmieniono
        self._dokument: dict | None = None

        self._etykieta_ladowania = ctk.CTkLabel(
            self,
            text="Ładowanie...",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        self._etykieta_ladowania.pack(expand=True)

        self._zaladuj(dokument_id)

    def _zaladuj(self, dokument_id: int, odswiezenie: bool = False) -> None:
        def zadanie():
            dokument = api_client.pobierz_dokument_magazynowy(dokument_id)
            magazyny = api_client.pobierz_magazyny(tylko_aktywne=False, limit=200)
            produkty = api_client.pobierz_produkty(tylko_aktywne=False, limit=200)
            faktura_numer = None
            if dokument.get("faktura_powiazana_id"):
                faktura = api_client.pobierz_fakture(dokument["faktura_powiazana_id"])
                faktura_numer = faktura["numer"]
            return dokument, magazyny, produkty, faktura_numer

        def sukces(wynik) -> None:
            dokument, magazyny, produkty, faktura_numer = wynik
            if odswiezenie:
                for dziecko in self.winfo_children():
                    dziecko.destroy()
            else:
                self._etykieta_ladowania.destroy()
            self._zbuduj_widok(dokument, magazyny, produkty, faktura_numer)

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)
            if not odswiezenie:
                self.destroy()

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zbuduj_widok(
        self,
        dokument: dict,
        magazyny: list[dict],
        produkty: list[dict],
        faktura_numer: str | None,
    ) -> None:
        self._dokument = dokument
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        magazyny_wg_id = {m["id"]: m["nazwa"] for m in magazyny}
        produkty_wg_id = {p["id"]: p for p in produkty}

        naglowek = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        naglowek.grid(
            row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0)
        )

        wiersz_tytulu = ctk.CTkFrame(naglowek, fg_color="transparent")
        wiersz_tytulu.pack(
            fill="x", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY)
        )
        tytul_tekst = (
            f"{formatowanie.formatuj_typ_dokumentu_magazynowego(dokument['typ'])} "
            f"— {dokument['numer']}"
        )
        ctk.CTkLabel(
            wiersz_tytulu,
            text=tytul_tekst,
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(side="left")
        ctk.CTkLabel(
            wiersz_tytulu,
            text=formatowanie.formatuj_status_dokumentu_magazynowego(dokument["status"]),
            font=styl.CZCIONKA_ETYKIETA,
            text_color=formatowanie.kolor_statusu_dokumentu_magazynowego(dokument["status"]),
        ).pack(side="left", padx=(styl.ODSTEP_SREDNI, 0))

        wiersze_info = [
            ("Data dokumentu", formatowanie.formatuj_date(dokument["data_dokumentu"])),
        ]
        if dokument.get("magazyn_zrodlowy_id"):
            wiersze_info.append(
                ("Magazyn źródłowy", magazyny_wg_id.get(dokument["magazyn_zrodlowy_id"], "—"))
            )
        if dokument.get("magazyn_docelowy_id"):
            wiersze_info.append(
                ("Magazyn docelowy", magazyny_wg_id.get(dokument["magazyn_docelowy_id"], "—"))
            )
        if faktura_numer:
            wiersze_info.append(("Powiązana faktura", faktura_numer))

        for etykieta, wartosc in wiersze_info:
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
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                anchor="w",
            ).pack(side="left")
        ctk.CTkFrame(naglowek, fg_color="transparent", height=styl.ODSTEP_MALY).pack()

        if dokument["status"] == "roboczy":
            pasek_akcji = ctk.CTkFrame(naglowek, fg_color="transparent")
            pasek_akcji.pack(
                fill="x", padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_SREDNI)
            )
            ctk.CTkButton(
                pasek_akcji,
                text="Edytuj",
                font=styl.CZCIONKA_TRESC,
                fg_color="transparent",
                border_width=1,
                border_color=styl.KOLOR_OBRAMOWANIE,
                text_color=styl.KOLOR_TEKST_GLOWNY,
                hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                command=self._edytuj,
            ).pack(side="left", padx=(0, styl.ODSTEP_MALY))
            self._przycisk_zatwierdz = ctk.CTkButton(
                pasek_akcji,
                text="Zatwierdź",
                font=styl.CZCIONKA_TRESC,
                fg_color=styl.KOLOR_AKCENT,
                hover_color=styl.KOLOR_AKCENT_HOVER,
                command=self._zatwierdz,
            )
            self._przycisk_zatwierdz.pack(side="left")

        ctk.CTkLabel(
            self,
            text="Pozycje",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=1, column=0, sticky="w", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, 0))

        tabela = Tabela(self, kolumny=KOLUMNY_POZYCJI)
        tabela.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_MALY, styl.ODSTEP_DUZY),
        )
        formatery = {
            "produkt": lambda p: (
                produkty_wg_id[p["produkt_id"]]["nazwa"]
                if p["produkt_id"] in produkty_wg_id
                else f"#{p['produkt_id']}"
            ),
            "ilosc": lambda p: formatowanie.formatuj_ilosc(
                p["ilosc"],
                produkty_wg_id.get(p["produkt_id"], {}).get("jednostka_miary"),
            ),
            "cena_zakupu": lambda p: (
                formatowanie.formatuj_kwote(p["cena_zakupu_netto_grosze"])
                if p.get("cena_zakupu_netto_grosze") is not None
                else "—"
            ),
            "notatka": lambda p: p.get("notatka") or "",
        }
        tabela.ustaw_dane(dokument["pozycje"], formatery=formatery)

    # -- akcje (Faza 27) --------------------------------------------------

    def _edytuj(self) -> None:
        FormularzDokumentuMagazynowego(
            self, on_zapisano=self._po_zapisie_edycji, dokument=self._dokument
        )

    def _po_zapisie_edycji(self) -> None:
        self._zaladuj(self._dokument_id, odswiezenie=True)
        if self._on_zmieniono:
            self._on_zmieniono()

    def _zatwierdz(self) -> None:
        if not messagebox.askyesno(
            "Zatwierdź dokument",
            f"Zatwierdzić dokument {self._dokument['numer']}? Po zatwierdzeniu "
            "nie będzie już można go edytować.",
            parent=self,
        ):
            return

        ustaw_tekst_ladowania(self._przycisk_zatwierdz, True, "Zatwierdź")

        def zadanie():
            return api_client.zatwierdz_dokument_magazynowy(self._dokument_id)

        def sukces(_wynik: dict) -> None:
            pokaz_toast(self, f"Dokument {self._dokument['numer']} zatwierdzony.")
            self._zaladuj(self._dokument_id, odswiezenie=True)
            if self._on_zmieniono:
                self._on_zmieniono()

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_zatwierdz, False, "Zatwierdź")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
