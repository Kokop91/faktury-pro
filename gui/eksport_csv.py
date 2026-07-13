import csv
from tkinter import filedialog
from typing import Callable

from gui.widgets_pomocnicze import komunikat_bledu, komunikat_info


def eksportuj_do_csv(
    rodzic,
    dane: list[dict],
    kolumny: list[tuple[str, str]],
    nazwa_pliku: str,
    formatery: dict[str, Callable[[dict], str]] | None = None,
) -> None:
    """Eksportuje `dane` do pliku CSV wybranego przez uzytkownika w oknie zapisu.
    `kolumny` to lista (klucz, naglowek) - naglowek trafia do pierwszego wiersza.
    Srednik jako separator i BOM (utf-8-sig), zeby plik otwieral sie poprawnie
    (w tym polskie znaki) w Excelu z domyslnymi ustawieniami regionalnymi PL.
    Uzywa wylacznie wbudowanej biblioteki `csv`, bez dodatkowych zaleznosci.
    """
    if not dane:
        komunikat_info(rodzic, "Brak danych do wyeksportowania.")
        return

    formatery = formatery or {}
    sciezka = filedialog.asksaveasfilename(
        parent=rodzic,
        title="Zapisz raport jako CSV",
        defaultextension=".csv",
        initialfile=nazwa_pliku,
        filetypes=[("Plik CSV", "*.csv")],
    )
    if not sciezka:
        return

    try:
        with open(sciezka, "w", newline="", encoding="utf-8-sig") as plik:
            zapisujacy = csv.writer(plik, delimiter=";")
            zapisujacy.writerow([naglowek for _klucz, naglowek in kolumny])
            for wiersz in dane:
                linia = []
                for klucz, _naglowek in kolumny:
                    formater = formatery.get(klucz)
                    linia.append(formater(wiersz) if formater else wiersz.get(klucz, ""))
                zapisujacy.writerow(linia)
    except OSError as e:
        komunikat_bledu(rodzic, f"Nie udało się zapisać pliku: {e}")
        return

    komunikat_info(rodzic, f"Zapisano plik:\n{sciezka}")
