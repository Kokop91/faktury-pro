import customtkinter as ctk

from gui import styl
from gui.windows.panel_raport_historii_ruchow import PanelRaportHistoriiRuchow
from gui.windows.panel_raport_ponizej_minimum import PanelRaportPonizejMinimum
from gui.windows.panel_stanow_magazynowych import PanelStanowMagazynowych


class PanelRaportow(ctk.CTkFrame):
    """Trzy podraporty w zagniezdzonej zakladce (mirror ukladu WidokMagazynu).
    "Stany aktualne" swiadomie reuzywa PanelStanowMagazynowych zamiast
    duplikowac go - GET /raporty/stany-aktualne nie istnieje jako osobny
    endpoint, bo GET /stany-magazynowe z Fazy 8 juz zwraca dokladnie to samo
    (patrz app/services/raporty_service.py)."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

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
        self._tabview.grid(row=0, column=0, sticky="nsew")

        tab_stany = self._tabview.add("Stany aktualne")
        tab_historia = self._tabview.add("Historia ruchów")
        tab_ponizej = self._tabview.add("Poniżej minimum")
        for tab in (tab_stany, tab_historia, tab_ponizej):
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self._panel_stany = PanelStanowMagazynowych(tab_stany)
        self._panel_stany.grid(row=0, column=0, sticky="nsew")

        self._panel_historia = PanelRaportHistoriiRuchow(tab_historia)
        self._panel_historia.grid(row=0, column=0, sticky="nsew")

        self._panel_ponizej = PanelRaportPonizejMinimum(tab_ponizej)
        self._panel_ponizej.grid(row=0, column=0, sticky="nsew")

    def odswiez(self) -> None:
        self._panel_stany.odswiez()
        self._panel_historia.odswiez()
        self._panel_ponizej.odswiez()
