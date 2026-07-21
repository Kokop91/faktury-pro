import shutil
from pathlib import Path
from tkinter import filedialog

from app.profil import katalog_aktywnego_profilu

# Logo firmy jest daną PER-PROFILU (Faza 25) - żyje w katalogu aktywnego
# profilu (app/profil.py:katalog_aktywnego_profilu), tak jak auth.json/
# ksef.json/ustawienia_profilu.json. W trybie deweloperskim (bez profili)
# spada na wspólny katalog globalny, dokładnie jak przed Fazą 25.
NAZWA_PODKATALOGU_LOGO = "logo"

ROZSZERZENIA_OBRAZOW = [("Obrazy", "*.png *.jpg *.jpeg"), ("Wszystkie pliki", "*.*")]


def _katalog_logo() -> Path:
    return katalog_aktywnego_profilu() / NAZWA_PODKATALOGU_LOGO


def katalog_logo() -> Path:
    """Publiczny dostep do katalogu logo (Faza 22 - kopia zapasowa musi
    umiec je zarchiwizowac/przywrocic, patrz gui/kopia_zapasowa.py)."""
    return _katalog_logo()


def wybierz_i_skopiuj_logo(rodzic) -> str | None:
    """Otwiera systemowe okno wyboru pliku obrazu i kopiuje go do lokalnego
    katalogu danych appki pod stala nazwa "logo.<rozszerzenie>" (jedna firma =
    jedno logo, nowy wybor nadpisuje poprzedni). Zwraca docelowa sciezke, albo
    None, jesli uzytkownik anulowal wybor."""
    sciezka = filedialog.askopenfilename(
        parent=rodzic,
        title="Wybierz logo firmy",
        filetypes=ROZSZERZENIA_OBRAZOW,
    )
    if not sciezka:
        return None

    zrodlo = Path(sciezka)
    katalog_docelowy = _katalog_logo()
    katalog_docelowy.mkdir(parents=True, exist_ok=True)
    docelowy = katalog_docelowy / f"logo{zrodlo.suffix.lower()}"
    shutil.copyfile(zrodlo, docelowy)
    return str(docelowy)
