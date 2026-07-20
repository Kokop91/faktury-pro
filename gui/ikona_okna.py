"""Ustawianie ikony okna/paska zadan (Faza 18A, naprawa) - NIE mylic z
gui/ikony.py (male ikonki rysowane programowo w przyciskach UI).

customtkinter/Tk nadpisuje ikone okna wlasna, domyslna ikona ("feather") przy
tworzeniu KAZDEGO roota (ctk.CTk()/tk.Tk()) - to dzieje sie niezaleznie od
tego, ze EXE(icon=...) w faktury_pro.spec poprawnie wypala icon.ico w zasoby
samego pliku .exe (ta ikona jest widoczna w Eksploratorze i na skrotach, ale
NIE trafia automatycznie na pasek zadan, bo Tk jawnie ustawia wlasna ikone
okna przy starcie). Kazdy root musi wiec jawnie wywolac root.iconbitmap(...)
sam - appka tworzy kilka NIEZALEZNYCH rootow po kolei (ekran logowania →
splash startu → kreator pierwszego uruchomienia → glowne okno), kazdy to
osobny interpreter Tcl, wiec ustawienie ikony na jednym nie przenosi sie na
kolejny.

`default=True` w iconbitmap ustawia rowniez ikone domyslna dla wszystkich
Toplevel utworzonych PO tym wywolaniu w ramach TEGO SAMEGO roota (np. dialogi
gui/windows/dialog_*.py oparte o ctk.CTkToplevel) - wystarczy wiec jedno
wywolanie w __init__ kazdego roota, bez dotykania kazdego dialogu osobno.
"""

from app.sciezki import katalog_bazowy


def sciezka_ikony():
    return katalog_bazowy() / "assets" / "icon.ico"


def ustaw_ikone(okno) -> None:
    sciezka = sciezka_ikony()
    if not sciezka.exists():
        return
    try:
        okno.iconbitmap(default=str(sciezka))
    except Exception:
        # iconbitmap z plikiem .ico dziala tylko na Windows (appka jest
        # Windows-only, patrz CLAUDE.md) - jeden cichy fallback zamiast
        # wywalania calego startu appki z powodu samej ikony.
        pass
