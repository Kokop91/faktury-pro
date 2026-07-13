import customtkinter as ctk

from gui import auth, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu


class _EkranLogowania(ctk.CTk):
    """Pierwsze okno appki - dziala jako wlasny root Tk (jeszcze przed
    uruchomieniem lokalnego serwera FastAPI, patrz gui/main.py), bo logowanie
    jest czysto lokalna operacja (plik + bcrypt), nie wymaga backendu.
    """

    def __init__(self):
        super().__init__()
        self.zalogowano = False
        self._tryb_ustawiania = not auth.czy_haslo_ustawione()

        self.title("Faktury Pro — logowanie")
        self.geometry("380x340")
        self.resizable(False, False)
        self.configure(fg_color=styl.KOLOR_TLO)

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(
            fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY
        )

        ctk.CTkLabel(
            kontener,
            text="Faktury Pro",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(pady=(0, styl.ODSTEP_MALY))

        if self._tryb_ustawiania:
            self._zbuduj_tryb_ustawiania(kontener)
        else:
            self._zbuduj_tryb_logowania(kontener)

    def _etykieta_pola(self, master, tekst: str) -> None:
        ctk.CTkLabel(
            master,
            text=tekst,
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

    def _zbuduj_tryb_ustawiania(self, kontener) -> None:
        ctk.CTkLabel(
            kontener,
            text="Pierwsze uruchomienie — ustaw hasło do aplikacji.",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            wraplength=300,
            justify="left",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._etykieta_pola(kontener, "Nowe hasło")
        self._pole_haslo = ctk.CTkEntry(kontener, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_haslo.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(kontener, "Powtórz hasło")
        self._pole_powtorz = ctk.CTkEntry(kontener, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_powtorz.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk = ctk.CTkButton(
            kontener,
            text="Ustaw hasło i uruchom",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._ustaw_haslo,
        )
        self._przycisk.pack(fill="x")

        self._pole_haslo.bind("<Return>", lambda _z: self._pole_powtorz.focus_set())
        self._pole_powtorz.bind("<Return>", lambda _z: self._ustaw_haslo())
        self._pole_haslo.focus_set()

    def _zbuduj_tryb_logowania(self, kontener) -> None:
        self._etykieta_pola(kontener, "Hasło")
        self._pole_haslo = ctk.CTkEntry(kontener, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_haslo.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk = ctk.CTkButton(
            kontener,
            text="Zaloguj",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zaloguj,
        )
        self._przycisk.pack(fill="x")

        self._pole_haslo.bind("<Return>", lambda _z: self._zaloguj())
        self._pole_haslo.focus_set()

    def _ustaw_przycisk_aktywny(self, aktywny: bool) -> None:
        self._przycisk.configure(state="normal" if aktywny else "disabled")

    def _ustaw_haslo(self) -> None:
        haslo = self._pole_haslo.get()
        powtorz = self._pole_powtorz.get()

        if len(haslo) < 4:
            komunikat_bledu(self, "Hasło musi mieć co najmniej 4 znaki.")
            return
        if haslo != powtorz:
            komunikat_bledu(self, "Hasła nie są identyczne.")
            return

        self._ustaw_przycisk_aktywny(False)

        def zadanie():
            auth.ustaw_haslo(haslo)

        def sukces(_wynik) -> None:
            self.zalogowano = True
            self.destroy()

        def blad(e) -> None:
            self._ustaw_przycisk_aktywny(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)

    def _zaloguj(self) -> None:
        haslo = self._pole_haslo.get()
        if not haslo:
            komunikat_bledu(self, "Podaj hasło.")
            return

        self._ustaw_przycisk_aktywny(False)

        def zadanie():
            return auth.zweryfikuj_haslo(haslo)

        def sukces(poprawne: bool) -> None:
            self._ustaw_przycisk_aktywny(True)
            if poprawne:
                self.zalogowano = True
                self.destroy()
            else:
                self._pole_haslo.delete(0, "end")
                komunikat_bledu(self, "Nieprawidłowe hasło.")

        def blad(e) -> None:
            self._ustaw_przycisk_aktywny(True)
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)


def pokaz_ekran_logowania() -> bool:
    """Blokuje az do zamkniecia okna logowania. Zwraca True, jesli uzytkownik
    poprawnie sie zalogowal (albo dopiero co ustawil haslo), False jesli okno
    zostalo zamkniete bez powodzenia (appka nie powinna wtedy startowac dalej)."""
    okno = _EkranLogowania()
    okno.mainloop()
    return okno.zalogowano
