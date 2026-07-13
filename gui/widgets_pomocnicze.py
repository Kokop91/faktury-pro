from tkinter import messagebox


def komunikat_bledu(rodzic, tekst: str, tytul: str = "Błąd") -> None:
    messagebox.showerror(tytul, tekst, parent=rodzic)


def komunikat_info(rodzic, tekst: str, tytul: str = "Informacja") -> None:
    messagebox.showinfo(tytul, tekst, parent=rodzic)


def komunikat_ostrzezenie(rodzic, tekst: str, tytul: str = "Ostrzeżenie") -> None:
    messagebox.showwarning(tytul, tekst, parent=rodzic)
