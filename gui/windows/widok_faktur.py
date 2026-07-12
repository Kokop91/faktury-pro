import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.widgets_pomocnicze import komunikat_bledu
from gui.windows.szczegoly_faktury import SzczegolyFaktury
from gui.windows.tabela import Tabela

KOLUMNY = [
    ("numer", "Numer", 2),
    ("klient", "Klient", 3),
    ("data_wystawienia", "Data wystawienia", 2),
    ("kwota_brutto", "Kwota brutto", 2),
    ("status", "Status", 2),
]


class WidokFaktur(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._klienci_wg_id: dict[int, str] = {}
        self._etykiety_statusow = ["Wszystkie"] + list(
            formatowanie.ETYKIETY_STATUSU.values()
        )
        self._klucze_wg_etykiety = {"Wszystkie": None, **{
            v: k for k, v in formatowanie.ETYKIETY_STATUSU.items()
        }}

        pasek_naglowka = ctk.CTkFrame(self, fg_color="transparent")
        pasek_naglowka.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
        )
        pasek_naglowka.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            pasek_naglowka,
            text="Faktury",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            pasek_naglowka,
            text="Status:",
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).grid(row=0, column=1, padx=(0, styl.ODSTEP_MALY))

        self._filtr_var = ctk.StringVar(value="Wszystkie")
        ctk.CTkOptionMenu(
            pasek_naglowka,
            values=self._etykiety_statusow,
            variable=self._filtr_var,
            command=lambda _wartosc: self.odswiez(),
            fg_color=styl.KOLOR_AKCENT,
            button_color=styl.KOLOR_AKCENT,
            button_hover_color=styl.KOLOR_AKCENT_HOVER,
        ).grid(row=0, column=2)

        self._tabela = Tabela(
            self, kolumny=KOLUMNY, on_wiersz_kliknij=self._otworz_szczegoly
        )
        self._tabela.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(0, styl.ODSTEP_DUZY),
        )

    def odswiez(self) -> None:
        try:
            # tylko_aktywni=False celowo - faktura moze odnosic sie do klienta,
            # ktory zostal miedzyczasie dezaktywowany (soft-delete).
            klienci = api_client.pobierz_klientow(tylko_aktywni=False, limit=200)
            self._klienci_wg_id = {k["id"]: k["nazwa"] for k in klienci}

            status_klucz = self._klucze_wg_etykiety.get(self._filtr_var.get())
            faktury = api_client.pobierz_faktury(status=status_klucz, limit=200)
        except api_client.ApiError as e:
            komunikat_bledu(self, e.komunikat)
            return

        formatery = {
            "klient": lambda w: self._klienci_wg_id.get(
                w["klient_id"], f"#{w['klient_id']}"
            ),
            "data_wystawienia": lambda w: formatowanie.formatuj_date(
                w["data_wystawienia"]
            ),
            "kwota_brutto": lambda w: formatowanie.formatuj_kwote(
                w["suma_brutto_grosze"], w["waluta"]
            ),
            "status": lambda w: formatowanie.formatuj_status(w["status"]),
        }
        self._tabela.ustaw_dane(faktury, formatery=formatery)

    def _otworz_szczegoly(self, wiersz: dict) -> None:
        nazwa_klienta = self._klienci_wg_id.get(wiersz["klient_id"])
        SzczegolyFaktury(self, faktura_id=wiersz["id"], nazwa_klienta=nazwa_klienta)
