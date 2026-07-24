import customtkinter as ctk

from gui import styl
from gui.windows.panel_dokumentow_magazynowych import PanelDokumentowMagazynowych
from gui.windows.panel_inwentaryzacji import PanelInwentaryzacji
from gui.windows.panel_magazynow import PanelMagazynow
from gui.windows.panel_produktow import PanelProduktow
from gui.windows.panel_raportow import PanelRaportow
from gui.windows.panel_stanow_magazynowych import PanelStanowMagazynowych


class WidokMagazynu(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=styl.KOLOR_TLO)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Magazyn",
            font=styl.NAGLOWEK_1,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=styl.ODSTEP_DUZY,
            pady=(styl.ODSTEP_DUZY, styl.ODSTEP_SREDNI),
        )

        self._tabview = ctk.CTkTabview(
            self,
            fg_color=styl.KOLOR_TLO,
            segmented_button_fg_color=styl.KOLOR_KARTA,
            segmented_button_selected_color=styl.KOLOR_AKCENT,
            segmented_button_selected_hover_color=styl.KOLOR_AKCENT_HOVER,
            segmented_button_unselected_color=styl.KOLOR_KARTA,
            segmented_button_unselected_hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY,
            text_color=styl.KOLOR_TEKST_GLOWNY,
        )
        self._tabview.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=styl.ODSTEP_DUZY,
            pady=(0, styl.ODSTEP_DUZY),
        )

        tab_produkty = self._tabview.add("Produkty")
        tab_magazyny = self._tabview.add("Magazyny")
        tab_dokumenty = self._tabview.add("Dokumenty")
        tab_stany = self._tabview.add("Stany magazynowe")
        tab_inwentaryzacja = self._tabview.add("Inwentaryzacja")
        tab_raporty = self._tabview.add("Raporty")
        for tab in (
            tab_produkty,
            tab_magazyny,
            tab_dokumenty,
            tab_stany,
            tab_inwentaryzacja,
            tab_raporty,
        ):
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self._panel_produktow = PanelProduktow(tab_produkty)
        self._panel_produktow.grid(row=0, column=0, sticky="nsew")

        self._panel_magazynow = PanelMagazynow(tab_magazyny)
        self._panel_magazynow.grid(row=0, column=0, sticky="nsew")

        self._panel_dokumentow = PanelDokumentowMagazynowych(
            tab_dokumenty, on_zmiana_stanu=self.odswiez
        )
        self._panel_dokumentow.grid(row=0, column=0, sticky="nsew")

        self._panel_stanow = PanelStanowMagazynowych(tab_stany)
        self._panel_stanow.grid(row=0, column=0, sticky="nsew")

        self._panel_inwentaryzacji = PanelInwentaryzacji(
            tab_inwentaryzacja, on_zmiana_stanu=self.odswiez
        )
        self._panel_inwentaryzacji.grid(row=0, column=0, sticky="nsew")

        self._panel_raportow = PanelRaportow(tab_raporty)
        self._panel_raportow.grid(row=0, column=0, sticky="nsew")

    def odswiez(self) -> None:
        # Wszystkie panele naraz - lokalne API jest szybkie, a to gwarantuje
        # swieze dane niezaleznie od tego, ktora zakladka jest aktualnie widoczna
        # (np. Dokumenty potrzebuja swiezej listy Magazynow do filtra).
        self._panel_produktow.odswiez()
        self._panel_magazynow.odswiez()
        self._panel_dokumentow.odswiez()
        self._panel_stanow.odswiez()
        self._panel_inwentaryzacji.odswiez()
        self._panel_raportow.odswiez()
