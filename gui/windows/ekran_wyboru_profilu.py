"""Ekran wyboru profilu firmy (Faza 25) - pierwszy ekran pokazywany przy
starcie appki w trybie produktowym (prywatny Postgres), PRZED dotychczasowym
ekranem logowania haslem (Faza 6) i PRZED kreatorem pierwszego uruchomienia
(Faza 18D). Wlasny root Tk (jak gui/windows/ekran_logowania.py) - dziala
wylacznie na lokalnym pliku profiles.json (gui/profile_rejestr.py), zero
polaczenia z baza/backendem, ktore jeszcze w ogole nie sa uruchomione.
"""

import customtkinter as ctk

from gui import formatowanie, profile_rejestr, styl
from gui.ikona_okna import ustaw_ikone


class WynikWyboruProfilu:
    def __init__(self, profil: profile_rejestr.Profil, nowy: bool):
        self.profil = profil
        self.nowy = nowy


class _EkranWyboruProfilu(ctk.CTk):
    def __init__(self):
        super().__init__()
        ustaw_ikone(self)
        self.wynik: WynikWyboruProfilu | None = None

        self.title("Faktury Pro — wybierz firmę")
        self.geometry("480x580")
        self.resizable(False, False)
        self.configure(fg_color=styl.KOLOR_TLO)

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)

        ctk.CTkLabel(
            kontener,
            text="Faktury Pro",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).pack(pady=(0, styl.ODSTEP_MIKRO))
        ctk.CTkLabel(
            kontener,
            text="Wybierz firmę, z którą chcesz pracować",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        ).pack(pady=(0, styl.ODSTEP_SREDNI))

        self._lista = ctk.CTkScrollableFrame(kontener, fg_color="transparent")
        self._lista.pack(fill="both", expand=True, pady=(0, styl.ODSTEP_SREDNI))

        ctk.CTkButton(
            kontener,
            text="+  Dodaj nową firmę",
            fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER,
            command=self._dodaj_nowa,
        ).pack(fill="x")

        self._zbuduj_liste()

    def _zbuduj_liste(self) -> None:
        for widget in self._lista.winfo_children():
            widget.destroy()

        profile = profile_rejestr.wczytaj_wszystkie()
        if not profile:
            ctk.CTkLabel(
                self._lista,
                text=(
                    "Brak jeszcze żadnej firmy na tym komputerze.\n"
                    "Kliknij „Dodaj nową firmę”, żeby zacząć."
                ),
                font=styl.CZCIONKA_TRESC,
                text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
                justify="left",
            ).pack(pady=styl.ODSTEP_DUZY)
            return

        for wpis in profile:
            self._karta_profilu(wpis)

    def _karta_profilu(self, wpis: profile_rejestr.Profil) -> None:
        karta = ctk.CTkFrame(
            self._lista,
            fg_color=styl.KOLOR_KARTA,
            corner_radius=styl.PROMIEN_NAROZNIKA,
            cursor="hand2",
        )
        karta.pack(fill="x", pady=(0, styl.ODSTEP_MALY))

        nazwa = wpis.nazwa_wyswietlana or "Nowa firma (nieskonfigurowana)"
        etyk_nazwa = ctk.CTkLabel(
            karta,
            text=nazwa,
            font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=styl.KOLOR_TEKST_GLOWNY,
            anchor="w",
        )
        etyk_nazwa.pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=(styl.ODSTEP_MALY, 0))

        tekst_daty = (
            f"Ostatnio używana: {formatowanie.formatuj_data_czas(wpis.ostatnio_uzywany)}"
            if wpis.ostatnio_uzywany
            else "Jeszcze nieuruchamiana"
        )
        etyk_data = ctk.CTkLabel(
            karta,
            text=tekst_daty,
            font=styl.CZCIONKA_DROBNA,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
            anchor="w",
        )
        etyk_data.pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_MALY))

        for widget in (karta, etyk_nazwa, etyk_data):
            widget.bind("<Button-1>", lambda _zdarzenie, w=wpis: self._wybierz(w))

    def _wybierz(self, wpis: profile_rejestr.Profil) -> None:
        self.wynik = WynikWyboruProfilu(wpis, nowy=False)
        self.destroy()

    def _dodaj_nowa(self) -> None:
        wpis = profile_rejestr.utworz_nowy_profil()
        self.wynik = WynikWyboruProfilu(wpis, nowy=True)
        self.destroy()


def pokaz_ekran_wyboru_profilu() -> "WynikWyboruProfilu | None":
    """Blokuje az do zamkniecia okna. Zwraca wybrany/nowo-utworzony profil,
    albo None jesli uzytkownik zamknal okno bez wyboru - appka powinna sie
    wtedy zakonczyc, dokladnie jak przy anulowanym ekranie logowania."""
    okno = _EkranWyboruProfilu()
    okno.mainloop()
    return okno.wynik
