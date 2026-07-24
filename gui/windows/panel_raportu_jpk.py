import os
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from gui import api_client, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, potwierdz, ustaw_tekst_ladowania
from gui.windows.dialog_gotowosci_jpk import DialogGotowosciJPK

MIESIACE = [
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
]

WARIANTY = {
    "Miesięczny (JPK_V7M)": "miesieczny",
    "Kwartalny (JPK_V7K)": "kwartalny",
}
PRZEDROSTKI_PLIKU = {"miesieczny": "JPK_V7M", "kwartalny": "JPK_V7K"}


class PanelRaportuJPK(ctk.CTkFrame):
    """Generowanie eksportu JPK_V7 (Faza 13) - dokument podatkowy, wiec zanim
    plik trafi na dysk uzytkownika: (1) API waliduje wygenerowany XML wzgledem
    prawdziwego, zbundlowanego schematu XSD Ministerstwa Finansow i NIGDY nie
    zwraca niepoprawnego pliku (patrz app/services/jpk_service.py), (2) przed
    wywolaniem generowania panel zawsze najpierw pyta /raporty/jpk-v7/sprawdz
    i pokazuje ostrzezenie (DialogGotowosciJPK) jesli w okresie sa faktury
    robocze albo klienci bez NIP - uzytkownik musi to swiadomie potwierdzic."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        karta = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.grid(row=0, column=0, sticky="new", padx=styl.ODSTEP_MALY, pady=styl.ODSTEP_MALY)
        karta.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            karta,
            text="Eksport JPK_V7 (ewidencja VAT + deklaracja)",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_MALY))

        ctk.CTkLabel(
            karta,
            text=(
                "Uwaga: appka nie prowadzi ewidencji zakupów/kosztów, więc plik nie "
                "zawiera VAT naliczonego z zakupów — kwota do zapłaty (P_51) może być "
                "zawyżona względem stanu po odliczeniach. Sprawdź to razem z księgową "
                "przed wysłaniem pliku do urzędu."
            ),
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_OSTRZEZENIE,
            anchor="w",
            justify="left",
            wraplength=700,
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_SREDNI))

        rok_biezacy = datetime.now().year
        lata = [str(r) for r in range(rok_biezacy - 3, rok_biezacy + 2)]

        ctk.CTkLabel(
            karta, text="Rok:", font=styl.CZCIONKA_ETYKIETA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=2, column=0, sticky="w", padx=(styl.ODSTEP_DUZY, 0))
        self._var_rok = ctk.StringVar(value=str(rok_biezacy))
        ctk.CTkOptionMenu(
            karta, values=lata, variable=self._var_rok,
            fg_color=styl.KOLOR_AKCENT, button_color=styl.KOLOR_AKCENT, button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=3, column=0, sticky="ew", padx=(styl.ODSTEP_DUZY, styl.ODSTEP_MALY), pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkLabel(
            karta, text="Miesiąc:", font=styl.CZCIONKA_ETYKIETA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=2, column=1, sticky="w")
        self._var_miesiac = ctk.StringVar(value=MIESIACE[datetime.now().month - 1])
        ctk.CTkOptionMenu(
            karta, values=MIESIACE, variable=self._var_miesiac, command=lambda _w: self._odswiez_info(),
            fg_color=styl.KOLOR_AKCENT, button_color=styl.KOLOR_AKCENT, button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=3, column=1, sticky="ew", padx=styl.ODSTEP_MALY, pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkLabel(
            karta, text="Rodzaj rozliczenia:", font=styl.CZCIONKA_ETYKIETA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=2, column=2, sticky="w")
        self._var_wariant = ctk.StringVar(value="Miesięczny (JPK_V7M)")
        ctk.CTkOptionMenu(
            karta, values=list(WARIANTY.keys()), variable=self._var_wariant, command=lambda _w: self._odswiez_info(),
            fg_color=styl.KOLOR_AKCENT, button_color=styl.KOLOR_AKCENT, button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=3, column=2, sticky="ew", padx=(styl.ODSTEP_MALY, styl.ODSTEP_DUZY), pady=(0, styl.ODSTEP_SREDNI))

        self._etykieta_info = ctk.CTkLabel(
            karta, text="", font=styl.CZCIONKA_DROBNA, text_color=styl.KOLOR_TEKST_DRUGORZEDNY, anchor="w",
        )
        self._etykieta_info.grid(row=4, column=0, columnspan=3, sticky="w", padx=styl.ODSTEP_DUZY)

        self._przycisk_generuj = ctk.CTkButton(
            karta,
            text="Generuj JPK_V7",
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._na_generuj,
        )
        self._przycisk_generuj.grid(
            row=5, column=0, columnspan=3, sticky="w", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_SREDNI, styl.ODSTEP_DUZY)
        )

        self._odswiez_info()

    def odswiez(self) -> None:
        self._odswiez_info()

    def _wybor(self) -> tuple[int, int, str]:
        return int(self._var_rok.get()), MIESIACE.index(self._var_miesiac.get()) + 1, WARIANTY[self._var_wariant.get()]

    def _odswiez_info(self) -> None:
        _rok, miesiac, wariant = self._wybor()
        zawiera_deklaracje = wariant == "miesieczny" or miesiac % 3 == 0
        if zawiera_deklaracje:
            tekst = "Ten plik będzie zawierał ewidencję VAT oraz deklarację (podsumowanie kwoty do zapłaty)."
        else:
            tekst = (
                "Rozliczenie kwartalne poza 3./6./9./12. miesiącem — ten plik zawiera "
                "samą ewidencję VAT, bez deklaracji (ta zostanie dołączona w ostatnim "
                "miesiącu kwartału)."
            )
        self._etykieta_info.configure(text=tekst)

    def _na_generuj(self) -> None:
        rok, miesiac, wariant = self._wybor()
        ustaw_tekst_ladowania(self._przycisk_generuj, True, "Generuj JPK_V7", "Sprawdzanie okresu...")

        def zadanie():
            return api_client.sprawdz_gotowosc_jpk(rok, miesiac)

        def sukces(wynik: dict) -> None:
            ustaw_tekst_ladowania(self._przycisk_generuj, False, "Generuj JPK_V7")
            if wynik.get("problemy"):
                DialogGotowosciJPK(
                    self, wynik, on_kontynuuj=lambda: self._generuj_i_zapisz(rok, miesiac, wariant)
                )
            else:
                self._generuj_i_zapisz(rok, miesiac, wariant)

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_generuj, False, "Generuj JPK_V7")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _generuj_i_zapisz(self, rok: int, miesiac: int, wariant: str) -> None:
        ustaw_tekst_ladowania(self._przycisk_generuj, True, "Generuj JPK_V7", "Generowanie i walidacja pliku...")

        def zadanie():
            return api_client.pobierz_jpk_v7(rok, miesiac, wariant)

        def sukces(tresc: bytes) -> None:
            ustaw_tekst_ladowania(self._przycisk_generuj, False, "Generuj JPK_V7")
            nazwa_domyslna = f"{PRZEDROSTKI_PLIKU[wariant]}_{rok}-{miesiac:02d}.xml"
            sciezka = filedialog.asksaveasfilename(
                parent=self,
                title="Zapisz plik JPK_V7",
                defaultextension=".xml",
                initialfile=nazwa_domyslna,
                filetypes=[("Plik XML", "*.xml")],
            )
            if not sciezka:
                return
            try:
                with open(sciezka, "wb") as plik:
                    plik.write(tresc)
            except OSError as e:
                komunikat_bledu(self, f"Nie udało się zapisać pliku: {e}")
                return
            if potwierdz(
                self,
                f"Zapisano plik:\n{sciezka}\n\nOtworzyć folder z plikiem?",
                tytul="Zapisano",
                tekst_tak="Otwórz folder",
                tekst_nie="Zamknij",
            ):
                os.startfile(os.path.dirname(sciezka))

        def blad(e: api_client.ApiError) -> None:
            ustaw_tekst_ladowania(self._przycisk_generuj, False, "Generuj JPK_V7")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
