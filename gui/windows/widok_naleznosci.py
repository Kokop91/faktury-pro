import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.szczegoly_faktury import SzczegolyFaktury
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("numer", "Numer", 2),
    ("klient", "Klient", 3),
    ("termin_platnosci", "Termin płatności", 2),
    ("kwota_brutto", "Kwota brutto", 2),
    ("kwota_pozostala", "Pozostało do zapłaty", 2),
    ("status", "Status", 2),
]


class WidokNaleznosci(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._klienci_wg_id: dict[int, str] = {}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_MALY),
        )

        ctk.CTkLabel(
            pasek_naglowka,
            text="Należności",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(anchor="w")

        self._etykieta_sumy = ctk.CTkLabel(
            self,
            text="",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        )
        self._etykieta_sumy.grid(
            row=1, column=0, sticky="w", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_SREDNI)
        )

        self._tabela = Tabela(
            self, kolumny=KOLUMNY, on_wiersz_kliknij=self._otworz_szczegoly
        )
        self._tabela.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(0, styl.ODSTEP_DUZY),
        )

    def odswiez(self) -> None:
        def zadanie():
            # tylko_aktywni=False celowo - faktura moze odnosic sie do klienta,
            # ktory zostal miedzyczasie dezaktywowany (soft-delete).
            klienci = api_client.pobierz_klientow(tylko_aktywni=False, limit=200)
            naleznosci = api_client.pobierz_naleznosci()
            return klienci, naleznosci

        def sukces(wynik) -> None:
            klienci, naleznosci = wynik
            self._klienci_wg_id = {k["id"]: k["nazwa"] for k in klienci}

            self._etykieta_sumy.configure(
                text=(
                    "Suma należności: "
                    f"{formatowanie.formatuj_kwote(naleznosci['suma_naleznosci_grosze'])}"
                )
            )

            formatery = {
                "klient": lambda w: self._klienci_wg_id.get(
                    w["klient_id"], f"#{w['klient_id']}"
                ),
                "termin_platnosci": lambda w: formatowanie.formatuj_date(
                    w["termin_platnosci"]
                ),
                "kwota_brutto": lambda w: formatowanie.formatuj_kwote(
                    w["suma_brutto_grosze"], w["waluta"]
                ),
                "kwota_pozostala": lambda w: formatowanie.formatuj_kwote(
                    w["kwota_pozostala_grosze"], w["waluta"]
                ),
                "status": lambda w: formatowanie.formatuj_status(
                    w["status_efektywny"]
                ),
            }
            kolory = {
                "status": lambda w: formatowanie.kolor_statusu(w["status_efektywny"]),
            }
            self._tabela.ustaw_dane(
                naleznosci["faktury"], formatery=formatery, kolory=kolory
            )

        def blad(e: api_client.ApiError) -> None:
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        nazwa_klienta = self._klienci_wg_id.get(wiersz["klient_id"])
        SzczegolyFaktury(
            self,
            faktura_id=wiersz["id"],
            nazwa_klienta=nazwa_klienta,
            on_zmiana=self.odswiez,
        )
