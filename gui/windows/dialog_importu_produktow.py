"""Import produktow z pliku CSV (Faza 26) - mirror dialog_importu_klientow.py,
patrz tam po ogolne uzasadnienie podzialu odpowiedzialnosci miedzy ten plik
(parsowanie tekstu z pliku) a backend (app/services/magazyn_service.py:
importuj_produkty - reguly biznesowe, duplikaty po nazwie).

Rozroznienie towar/usluga (Faza 7) dostaje dodatkowy element w kroku mapowania:
appka rozpoznaje typ z tekstu w zmapowanej kolumnie (tak/nie, towar/usluga...),
a dla wierszy gdzie sie to nie uda (albo kolumna w ogole nie jest zmapowana)
stosuje domyslny typ wybrany w tym samym kroku - PLAN wprost dopuszcza to jako
'usluga z mozliwoscia zbiorczej zmiany' (Produkt jest create-only, patrz
komentarz przy magazyn_service.utworz_produkt - appka nie ma dzis edycji typu
PO zapisie, wiec ten wybor musi zapasc PRZED importem, nie po)."""

from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.import_csv import normalizuj
from gui.windows.dialog_importu_csv import DialogImportuCsv

_POLA = [
    ("nazwa", "Nazwa *", True, ("nazwa", "name", "produkt", "towar", "usluga")),
    (
        "jednostka_miary",
        "Jednostka miary *",
        True,
        ("jednostka", "jm", "j.m.", "unit", "jednostka miary"),
    ),
    (
        "cena_netto_grosze",
        "Cena netto *",
        True,
        ("cena netto", "cena", "price", "cena jednostkowa", "cena netto (pln)"),
    ),
    ("koszt_zakupu_grosze", "Koszt zakupu", False, ("koszt zakupu", "koszt", "cost")),
    ("domyslna_stawka_vat", "Stawka VAT", False, ("vat", "stawka vat", "stawka")),
    (
        "jest_magazynowy",
        "Typ (towar / usługa)",
        False,
        ("typ", "rodzaj", "towar/usluga", "kategoria"),
    ),
    (
        "objety_zalacznikiem_15",
        "Załącznik nr 15 (MPP)",
        False,
        ("zalacznik 15", "zalacznik nr 15", "mpp", "split payment"),
    ),
]

_SLOWA_PRAWDA = {"towar", "tak", "1", "true", "magazynowy", "product", "yes", "y", "t"}
_SLOWA_FALSZ = {"usluga", "nie", "0", "false", "service", "no", "n"}

_ETYKIETA_USLUGA = "Usługa"
_ETYKIETA_TOWAR = "Towar magazynowy"


def _rozpoznaj_stawke_vat(tekst: str) -> str:
    znorm = normalizuj(tekst).replace("%", "").strip()
    if znorm in ("zw", "zw.", "zwolniony", "zwolniona"):
        return "zw"
    return znorm


class DialogImportuProduktow(DialogImportuCsv):
    KOLUMNY_PODGLADU = ["nazwa", "jednostka_miary", "cena_netto_grosze"]

    def __init__(self, master, on_zaimportowano: Callable[[], None]):
        super().__init__(master, "Importuj produkty z CSV", on_zaimportowano)

    def pola(self):
        return _POLA

    def zbuduj_dodatkowe_opcje_mapowania(self, master) -> None:
        ramka = ctk.CTkFrame(master, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA)
        ramka.grid(
            row=len(_POLA) + 1, column=0, columnspan=2, sticky="ew", pady=(styl.ODSTEP_SREDNI, 0)
        )

        ctk.CTkLabel(
            ramka,
            text="Domyślny typ produktu",
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        ).pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_MIKRO))
        ctk.CTkLabel(
            ramka,
            text=(
                "Stosowany dla wierszy, w których nie da się rozpoznać typu z pliku "
                "(kolumna niezmapowana albo z nierozpoznaną wartością)."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=600,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_MALY))

        self._var_domyslny_typ = ctk.StringVar(value=_ETYKIETA_USLUGA)
        ctk.CTkSegmentedButton(
            ramka,
            values=[_ETYKIETA_USLUGA, _ETYKIETA_TOWAR],
            variable=self._var_domyslny_typ,
            font=styl.CZCIONKA_TRESC,
            selected_color=styl.KOLOR_AKCENT,
            selected_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_SREDNI))

    def koerencja_wiersza(self, surowe: dict[str, str]) -> tuple[dict | None, str | None]:
        nazwa = surowe.get("nazwa", "").strip()
        if not nazwa:
            return None, "brak nazwy (pole wymagane)"

        jednostka = surowe.get("jednostka_miary", "").strip()
        if not jednostka:
            return None, "brak jednostki miary (pole wymagane)"

        cena_tekst = surowe.get("cena_netto_grosze", "").strip()
        if not cena_tekst:
            return None, "brak ceny netto (pole wymagane)"
        try:
            cena_grosze = formatowanie.parsuj_kwote(cena_tekst, wymagaj_dodatniej=False)
        except ValueError as e:
            return None, f"nieprawidłowa cena netto „{cena_tekst}”: {e}"

        dane: dict = {
            "nazwa": nazwa,
            "jednostka_miary": jednostka,
            "cena_netto_grosze": cena_grosze,
        }

        koszt_tekst = surowe.get("koszt_zakupu_grosze", "").strip()
        if koszt_tekst:
            try:
                dane["koszt_zakupu_grosze"] = formatowanie.parsuj_kwote(
                    koszt_tekst, wymagaj_dodatniej=False
                )
            except ValueError as e:
                return None, f"nieprawidłowy koszt zakupu „{koszt_tekst}”: {e}"

        stawka_tekst = surowe.get("domyslna_stawka_vat", "").strip()
        if stawka_tekst:
            dane["domyslna_stawka_vat"] = _rozpoznaj_stawke_vat(stawka_tekst)

        typ_znorm = normalizuj(surowe.get("jest_magazynowy", ""))
        if typ_znorm in _SLOWA_PRAWDA:
            dane["jest_magazynowy"] = True
        elif typ_znorm in _SLOWA_FALSZ:
            dane["jest_magazynowy"] = False
        else:
            dane["jest_magazynowy"] = self._var_domyslny_typ.get() == _ETYKIETA_TOWAR

        zalacznik_znorm = normalizuj(surowe.get("objety_zalacznikiem_15", ""))
        dane["objety_zalacznikiem_15"] = zalacznik_znorm in _SLOWA_PRAWDA

        return dane, None

    def formatery_podgladu(self):
        return {
            "cena_netto_grosze": lambda w: (
                formatowanie.formatuj_kwote(w["cena_netto_grosze"])
                if isinstance(w.get("cena_netto_grosze"), int)
                else str(w.get("cena_netto_grosze", ""))
            ),
        }

    def wywolaj_podglad(self, wiersze: list[dict]) -> list[dict]:
        return api_client.podglad_importu_produktow(wiersze)

    def wywolaj_import(self, wiersze: list[dict]) -> list[dict]:
        return api_client.importuj_produkty(wiersze)
