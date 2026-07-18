"""Rozwiazywanie sciezek do wbudowanych zasobow appki (szablony PDF, schematy
XSD/XML) - dziala identycznie w trybie deweloperskim i w wersji spakowanej
PyInstallerem (Faza 18A).

W wersji spakowanej `__file__` modulow w app/ NIE wskazuje na prawdziwy plik na
dysku (kod jest skompilowany do archiwum PYZ) - jedynym niezawodnym, zalecanym
przez PyInstaller sposobem odnalezienia katalogu z dolaczonymi danymi jest
sprawdzenie sys._MEIPASS (ustawiane TYLKO gdy sys.frozen jest True, zarowno w
trybie --onedir jak i --onefile). W trybie deweloperskim nie ma sys._MEIPASS,
wiec baza to zwyczajnie katalog glowny repozytorium (rodzic katalogu app/).
"""

import sys
from pathlib import Path


def katalog_bazowy() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent
