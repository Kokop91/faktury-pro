import customtkinter as ctk

from gui import auth, styl
from gui.ikona_okna import ustaw_ikone
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu


class _EkranLogowania(ctk.CTk):
    """Pierwsze okno appki gdy haslo juz istnieje - dziala jako wlasny root Tk
    (jeszcze przed uruchomieniem lokalnego serwera FastAPI, patrz gui/main.py),
    bo logowanie jest czysto lokalna operacja (plik + bcrypt), nie wymaga
    backendu. Gdy hasla jeszcze nie ma (pierwsze uruchomienie appki), ten
    ekran w ogole sie nie pokazuje - ustawienie hasla jest wtedy Krokiem 2
    kreatora pierwszego uruchomienia (Faza 18D,
    gui/windows/kreator_pierwszego_uruchomienia.py), ktory rusza pozniej, po
    starcie backendu."""

    def __init__(self):
        super().__init__()
        ustaw_ikone(self)
        self.zalogowano = False

        self.title("Faktury Pro — logowanie")
        self.geometry("380x260")
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

    def _etykieta_pola(self, master, tekst: str) -> None:
        ctk.CTkLabel(
            master,
            text=tekst,
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_ETYKIETA))

    def _ustaw_przycisk_aktywny(self, aktywny: bool) -> None:
        self._przycisk.configure(state="normal" if aktywny else "disabled")

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
    poprawnie sie zalogowal, False jesli okno zostalo zamkniete bez powodzenia
    (appka nie powinna wtedy startowac dalej)."""
    okno = _EkranLogowania()
    okno.mainloop()
    return okno.zalogowano
