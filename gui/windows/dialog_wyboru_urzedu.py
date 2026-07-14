from typing import Callable

import customtkinter as ctk

from gui import styl


class DialogWyboruUrzeduSkarbowego(ctk.CTkToplevel):
    """Wyszukiwarka urzedu skarbowego (Faza 13) - 400 pozycji to za duzo dla
    zwyklego OptionMenu, a kod urzedu jest 4-cyfrowym, scisle enumerowanym
    polem w schemacie JPK_V7 (KodUrzedu), wiec uzytkownik NIE powinien go
    wpisywac z pamieci - wybiera z listy po nazwie miejscowosci/urzedu."""

    def __init__(self, master, urzedy: list[dict], on_wybierz: Callable[[dict], None]):
        super().__init__(master)
        self.title("Wybierz urząd skarbowy")
        self.geometry("480x560")
        self.configure(fg_color=styl.KOLOR_TLO)
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda _z: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._urzedy = urzedy
        self._on_wybierz = on_wybierz

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._var_szukaj = ctk.StringVar()
        self._var_szukaj.trace_add("write", lambda *_a: self._odswiez_liste())
        pole_szukaj = ctk.CTkEntry(
            self, font=styl.CZCIONKA_TRESC, textvariable=self._var_szukaj,
            placeholder_text="Szukaj po nazwie urzędu lub miejscowości...",
        )
        pole_szukaj.grid(row=0, column=0, sticky="ew", padx=styl.ODSTEP_DUZY, pady=(styl.ODSTEP_DUZY, styl.ODSTEP_MALY))
        pole_szukaj.focus_set()

        self._lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._lista.grid(row=1, column=0, sticky="nsew", padx=styl.ODSTEP_DUZY, pady=(0, styl.ODSTEP_DUZY))
        self._lista.grid_columnconfigure(0, weight=1)

        self._odswiez_liste()

    def _odswiez_liste(self) -> None:
        for widget in self._lista.winfo_children():
            widget.destroy()

        fraza = self._var_szukaj.get().strip().lower()
        pasujace = [
            u for u in self._urzedy
            if fraza in u["nazwa"].lower() or fraza in u["kod"]
        ] if fraza else self._urzedy

        for indeks, urzad in enumerate(pasujace[:200]):
            ctk.CTkButton(
                self._lista,
                text=f"{urzad['kod']} — {urzad['nazwa'].title()}",
                font=styl.CZCIONKA_TRESC,
                anchor="w",
                fg_color="transparent",
                text_color=styl.KOLOR_TEKST_GLOWNY,
                hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
                command=lambda u=urzad: self._wybierz(u),
            ).grid(row=indeks, column=0, sticky="ew", pady=(0, styl.ODSTEP_MIKRO))

    def _wybierz(self, urzad: dict) -> None:
        self.destroy()
        self._on_wybierz(urzad)
