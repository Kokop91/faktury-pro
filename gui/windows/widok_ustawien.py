import customtkinter as ctk

from gui import auth, styl
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import komunikat_bledu, komunikat_info


class WidokUstawien(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)

        karta = ctk.CTkFrame(
            self, fg_color=styl.KOLOR_KARTA, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        karta.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            karta,
            text="Zmiana hasła",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
            anchor="w",
        )

        wewnatrz = ctk.CTkFrame(karta, fg_color="transparent", width=320)
        wewnatrz.pack(padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY), fill="x")

        self._etykieta_pola(wewnatrz, "Obecne hasło")
        self._pole_stare = ctk.CTkEntry(wewnatrz, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_stare.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Nowe hasło")
        self._pole_nowe = ctk.CTkEntry(wewnatrz, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_nowe.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        self._etykieta_pola(wewnatrz, "Powtórz nowe hasło")
        self._pole_powtorz = ctk.CTkEntry(wewnatrz, show="•", font=styl.CZCIONKA_TRESC)
        self._pole_powtorz.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        self._przycisk = ctk.CTkButton(
            wewnatrz,
            text="Zmień hasło",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._zmien_haslo,
        )
        self._przycisk.pack(fill="x")

    def _etykieta_pola(self, master, tekst: str) -> None:
        ctk.CTkLabel(
            master,
            text=tekst,
            font=styl.CZCIONKA_ETYKIETA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

    def odswiez(self) -> None:
        pass

    def _zmien_haslo(self) -> None:
        stare = self._pole_stare.get()
        nowe = self._pole_nowe.get()
        powtorz = self._pole_powtorz.get()

        if not stare:
            komunikat_bledu(self, "Podaj obecne hasło.")
            return
        if len(nowe) < 4:
            komunikat_bledu(self, "Nowe hasło musi mieć co najmniej 4 znaki.")
            return
        if nowe != powtorz:
            komunikat_bledu(self, "Nowe hasła nie są identyczne.")
            return

        self._przycisk.configure(state="disabled")

        def zadanie() -> bool:
            if not auth.zweryfikuj_haslo(stare):
                return False
            auth.ustaw_haslo(nowe)
            return True

        def sukces(udane: bool) -> None:
            self._przycisk.configure(state="normal")
            if udane:
                self._pole_stare.delete(0, "end")
                self._pole_nowe.delete(0, "end")
                self._pole_powtorz.delete(0, "end")
                komunikat_info(self, "Hasło zostało zmienione.")
            else:
                komunikat_bledu(self, "Nieprawidłowe obecne hasło.")

        def blad(e) -> None:
            self._przycisk.configure(state="normal")
            komunikat_bledu(self, e.komunikat)

        uruchom_w_tle(self, zadanie, sukces, blad)
