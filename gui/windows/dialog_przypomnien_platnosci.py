from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, komunikat_ostrzezenie, pokaz_toast, ustaw_tekst_ladowania


class DialogPrzypomnienPlatnosci(ctk.CTkToplevel):
    """Okno startowe (Faza 23) - ten sam wzorzec co
    DialogZaleglychCyklicznych (Faza 15): appka desktopowa nie dziala 24/7,
    wiec zamiast systemowego harmonogramu sprawdzamy kandydatow RAZ, przy
    kazdym uruchomieniu. Nigdy nie wysyla nic automatycznie - to zawsze
    swiadoma decyzja uzytkownika (Wyslij wybrane/wszystkie), z opcja
    "Pozniej" (proste zamkniecie bez potwierdzenia)."""

    def __init__(self, master, kandydaci: list[dict], on_wyslano: Callable[[], None]):
        super().__init__(master)
        self.title("Przypomnienia o płatnościach do wysłania")
        self.geometry("680x560")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda _z: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._kandydaci = kandydaci
        self._on_wyslano = on_wyslano
        self._zaznaczenia: list[ctk.BooleanVar] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text=f"Do wysłania: {len(kandydaci)} przypomnień",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(row=0, column=0, sticky="w", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI))

        przewijany = ctk.CTkScrollableFrame(self, fg_color="transparent")
        przewijany.grid(row=1, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY)
        przewijany.grid_columnconfigure(0, weight=1)

        for indeks, pozycja in enumerate(kandydaci):
            ma_email = bool(pozycja.get("klient_email"))
            zaznaczona = ctk.BooleanVar(value=ma_email)
            self._zaznaczenia.append(zaznaczona)

            wiersz = ctk.CTkFrame(
                przewijany, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
            )
            wiersz.grid(row=indeks, column=0, sticky="ew", pady=(0, styl.ODSTEP_MALY))
            wiersz.grid_columnconfigure(1, weight=1)

            ctk.CTkCheckBox(
                wiersz,
                text="",
                variable=zaznaczona,
                width=20,
                state="normal" if ma_email else "disabled",
                fg_color=styl.KOLOR_AKCENT,
                hover_color=styl.KOLOR_AKCENT_HOVER,
            ).grid(row=0, column=0, rowspan=2, padx=(styl.ODSTEP_SREDNI, styl.ODSTEP_MALY), pady=styl.ODSTEP_MALY)

            opis_email = pozycja["klient_email"] if ma_email else "brak adresu e-mail — pominięte"
            tekst_opisu = (
                f"{pozycja['klient_nazwa']} — faktura {pozycja['numer_faktury']} "
                f"(termin {formatowanie.formatuj_date(pozycja['termin_platnosci'])})"
            )
            ctk.CTkLabel(
                wiersz, text=tekst_opisu, font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_GLOWNY, anchor="w",
            ).grid(row=0, column=1, sticky="w", pady=(styl.ODSTEP_MALY, 0))
            ctk.CTkLabel(
                wiersz, text=opis_email, font=styl.CZCIONKA_DROBNA,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY if ma_email else styl.KOLOR_BLAD, anchor="w",
            ).grid(row=1, column=1, sticky="w", pady=(0, styl.ODSTEP_MALY))

            ctk.CTkLabel(
                wiersz,
                text=formatowanie.formatuj_typ_przypomnienia(pozycja["typ"]),
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=formatowanie.kolor_typu_przypomnienia(pozycja["typ"]),
            ).grid(row=0, column=2, rowspan=2, padx=styl.ODSTEP_SREDNI)

            ctk.CTkLabel(
                wiersz,
                text=formatowanie.formatuj_kwote(pozycja["kwota_pozostala_grosze"], pozycja["waluta"]),
                font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_TEKST_GLOWNY,
            ).grid(row=0, column=3, rowspan=2, padx=(0, styl.ODSTEP_SREDNI))

        pasek_przyciskow = ctk.CTkFrame(self, fg_color="transparent")
        pasek_przyciskow.grid(row=2, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)
        pasek_przyciskow.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            pasek_przyciskow,
            text="Później",
            fg_color="transparent",
            border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_wybrane = ctk.CTkButton(
            pasek_przyciskow,
            text="Wyślij wybrane",
            fg_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            hover_color=styl.KOLOR_TEKST_GLOWNY,
            command=self._wyslij_wybrane,
        )
        self._przycisk_wybrane.grid(row=0, column=1, sticky="ew", padx=(0, styl.ODSTEP_MALY))
        self._przycisk_wszystkie = ctk.CTkButton(
            pasek_przyciskow,
            text="Wyślij wszystkie",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._wyslij_wszystkie,
        )
        self._przycisk_wszystkie.grid(row=0, column=2, sticky="ew")

    def _ustaw_przyciski_aktywne(self, aktywne: bool) -> None:
        stan = "normal" if aktywne else "disabled"
        self._przycisk_wybrane.configure(state=stan)
        self._przycisk_wszystkie.configure(state=stan)

    def _wyslij_wybrane(self) -> None:
        wybrane = [
            {"faktura_id": pozycja["faktura_id"], "typ": pozycja["typ"]}
            for pozycja, zaznaczona in zip(self._kandydaci, self._zaznaczenia)
            if zaznaczona.get()
        ]
        if not wybrane:
            komunikat_bledu(self, "Zaznacz co najmniej jedno przypomnienie do wysłania.")
            return
        self._wyslij(wybrane, "Wyślij wybrane")

    def _wyslij_wszystkie(self) -> None:
        wszystkie = [
            {"faktura_id": pozycja["faktura_id"], "typ": pozycja["typ"]}
            for pozycja in self._kandydaci
            if pozycja.get("klient_email")
        ]
        if not wszystkie:
            komunikat_bledu(self, "Żaden z kandydatów nie ma adresu e-mail klienta.")
            return
        self._wyslij(wszystkie, "Wyślij wszystkie")

    def _wyslij(self, pozycje: list[dict], tekst_przycisku: str) -> None:
        self._ustaw_przyciski_aktywne(False)
        ustaw_tekst_ladowania(self._przycisk_wszystkie, True, "Wyślij wszystkie", "Wysyłanie...")

        def zadanie():
            return api_client.wyslij_przypomnienia(pozycje)

        def sukces(wyniki: list[dict]) -> None:
            master = self.master
            udane = sum(1 for w in wyniki if w["powodzenie"])
            nieudane = [w for w in wyniki if not w["powodzenie"]]
            self._on_wyslano()
            self.destroy()
            if nieudane:
                szczegoly = "\n".join(f"- {w['komunikat']}" for w in nieudane)
                komunikat_ostrzezenie(
                    master,
                    f"Wysłano {udane} z {len(wyniki)} przypomnień. Błędy:\n\n{szczegoly}",
                )
            else:
                pokaz_toast(master, f"Wysłano {udane} przypomnień.")

        def blad(e: api_client.ApiError) -> None:
            self._ustaw_przyciski_aktywne(True)
            ustaw_tekst_ladowania(self._przycisk_wszystkie, False, "Wyślij wszystkie")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
