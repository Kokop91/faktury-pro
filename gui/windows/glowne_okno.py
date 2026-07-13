import customtkinter as ctk

from gui import styl
from gui.windows.widok_faktur import WidokFaktur
from gui.windows.widok_klientow import WidokKlientow
from gui.windows.widok_naleznosci import WidokNaleznosci


class GlowneOkno(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Faktury Pro")
        self.geometry("1150x720")
        self.minsize(900, 600)
        self.configure(fg_color=styl.KOLOR_TLO)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._pasek_boczny = _PasekBoczny(self, on_nawigacja=self._pokaz_widok)
        self._pasek_boczny.grid(row=0, column=0, sticky="nsw")

        self._kontener = ctk.CTkFrame(self, fg_color=styl.KOLOR_TLO, corner_radius=0)
        self._kontener.grid(row=0, column=1, sticky="nsew")
        self._kontener.grid_columnconfigure(0, weight=1)
        self._kontener.grid_rowconfigure(0, weight=1)

        self._widoki: dict[str, ctk.CTkFrame] = {}

        self._pokaz_widok("faktury")

    def _utworz_widok(self, klucz: str) -> ctk.CTkFrame:
        if klucz == "faktury":
            return WidokFaktur(self._kontener)
        if klucz == "naleznosci":
            return WidokNaleznosci(self._kontener)
        if klucz == "klienci":
            return WidokKlientow(self._kontener)
        if klucz == "ustawienia":
            return _WidokUstawien(self._kontener)
        raise ValueError(f"Nieznany widok: {klucz}")

    def _pokaz_widok(self, klucz: str) -> None:
        if klucz not in self._widoki:
            widok = self._utworz_widok(klucz)
            widok.grid(row=0, column=0, sticky="nsew")
            self._widoki[klucz] = widok

        self._widoki[klucz].tkraise()
        self._pasek_boczny.ustaw_aktywny(klucz)

        odswiez = getattr(self._widoki[klucz], "odswiez", None)
        if callable(odswiez):
            odswiez()


class _PasekBoczny(ctk.CTkFrame):
    POZYCJE = [
        ("faktury", "Faktury"),
        ("naleznosci", "Należności"),
        ("klienci", "Klienci"),
        ("ustawienia", "Ustawienia"),
    ]

    def __init__(self, master, on_nawigacja):
        super().__init__(
            master,
            width=styl.SZEROKOSC_SIDEBAR,
            fg_color=styl.KOLOR_SIDEBAR,
            corner_radius=0,
        )
        self.grid_propagate(False)
        self.on_nawigacja = on_nawigacja
        self._przyciski: dict[str, ctk.CTkButton] = {}

        tytul = ctk.CTkLabel(
            self,
            text="Faktury Pro",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_SIDEBAR_TEKST,
        )
        tytul.pack(
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY * 2, styl.ODSTEP_DUZY),
            anchor="w",
        )

        for klucz, etykieta in self.POZYCJE:
            przycisk = ctk.CTkButton(
                self,
                text=etykieta,
                font=styl.CZCIONKA_TRESC,
                anchor="w",
                corner_radius=styl.PROMIEN_NAROZNIKA,
                fg_color="transparent",
                hover_color=styl.KOLOR_AKCENT_HOVER,
                text_color=styl.KOLOR_SIDEBAR_TEKST,
                command=lambda k=klucz: self.on_nawigacja(k),
            )
            przycisk.pack(
                fill="x", padx=styl.ODSTEP_SREDNI, pady=(0, styl.ODSTEP_MALY)
            )
            self._przyciski[klucz] = przycisk

    def ustaw_aktywny(self, klucz: str) -> None:
        for klucz_przycisku, przycisk in self._przyciski.items():
            przycisk.configure(
                fg_color=styl.KOLOR_AKCENT
                if klucz_przycisku == klucz
                else "transparent"
            )


class _WidokUstawien(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        etykieta = ctk.CTkLabel(
            self,
            text="Ustawienia — dostępne w kolejnej fazie.",
            font=styl.NAGLOWEK_2,
            text_color=styl.KOLOR_TEKST_DRUGORZEDNY,
        )
        etykieta.place(relx=0.5, rely=0.5, anchor="center")

    def odswiez(self) -> None:
        pass
