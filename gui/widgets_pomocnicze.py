from tkinter import messagebox

import customtkinter as ctk

from gui import styl


def komunikat_bledu(rodzic, tekst: str, tytul: str = "Błąd") -> None:
    messagebox.showerror(tytul, tekst, parent=rodzic)


def komunikat_info(rodzic, tekst: str, tytul: str = "Informacja") -> None:
    messagebox.showinfo(tytul, tekst, parent=rodzic)


def komunikat_ostrzezenie(rodzic, tekst: str, tytul: str = "Ostrzeżenie") -> None:
    messagebox.showwarning(tytul, tekst, parent=rodzic)


def ustaw_tekst_ladowania(
    przycisk: ctk.CTkButton,
    w_trakcie: bool,
    tekst_zwykly: str,
    tekst_ladowania: str = "Zapisywanie...",
) -> None:
    """Wskaznik ladowania dla akcji sieciowych spod przycisku (zapis, PDF,
    generowanie dokumentu) - zamiast samego wyszarzenia przycisku, tekst tez
    mowi co sie dzieje (Faza 16C, punkt 1)."""
    przycisk.configure(
        state="disabled" if w_trakcie else "normal",
        text=tekst_ladowania if w_trakcie else tekst_zwykly,
    )


class Banner(ctk.CTkFrame):
    """Nieblokujacy banner bledu walidacji, osadzony w formularzu (Faza 16C,
    punkt 2) - w odroznieniu od messagebox.showerror nie przerywa pracy
    modalnym oknem. Domyslnie ukryty; wolajacy rejestruje docelowa geometrie
    (pack lub grid) przez `ustaw_geometrie`, bo Banner nie wie, ktorego
    menedzera geometrii uzywa konkretny formularz."""

    def __init__(self, master):
        super().__init__(
            master, fg_color=styl.KOLOR_BLAD_TLO, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self._etykieta = ctk.CTkLabel(
            self,
            text="",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_BLAD,
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self._etykieta.pack(
            fill="x", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY
        )
        self._umiesc = lambda: None

    def ustaw_geometrie(self, umiesc) -> None:
        """`umiesc` to funkcja bezargumentowa wywolujaca .pack(...) albo
        .grid(...) z parametrami wlasciwymi dla danego formularza."""
        self._umiesc = umiesc

    def pokaz(self, tekst: str) -> None:
        self._etykieta.configure(text=tekst)
        self._umiesc()

    def ukryj(self) -> None:
        self.pack_forget()
        self.grid_forget()


_CZAS_TOASTU_MS = 3500

_KOLORY_TOASTU = {
    "sukces": (styl.KOLOR_SUKCES_TLO, styl.KOLOR_SUKCES),
    "blad": (styl.KOLOR_BLAD_TLO, styl.KOLOR_BLAD),
    "ostrzezenie": (styl.KOLOR_OSTRZEZENIE_TLO, styl.KOLOR_OSTRZEZENIE),
}


def pokaz_toast(widget, tekst: str, typ: str = "sukces") -> None:
    """Nieblokujacy komunikat sukcesu (Faza 16C, punkt 2) - znika sam po
    kilku sekundach, w przeciwienstwie do messagebox.showinfo. Zaczepiony o
    okno najwyzszego poziomu (`winfo_toplevel`) danego widgetu, zeby dzialal
    zarowno z widoku w glownym oknie, jak i z formularza w osobnym Toplevelu.
    Kolejny toast na tym samym oknie zastepuje poprzedni, zamiast sie stakowac."""
    root = widget.winfo_toplevel()
    poprzedni = getattr(root, "_aktywny_toast", None)
    if poprzedni is not None and poprzedni.winfo_exists():
        poprzedni.destroy()

    kolor_tla, kolor_tekstu = _KOLORY_TOASTU.get(typ, _KOLORY_TOASTU["sukces"])

    toast = ctk.CTkFrame(
        root, fg_color=kolor_tla, corner_radius=styl.PROMIEN_NAROZNIKA
    )
    ctk.CTkLabel(
        toast,
        text=tekst,
        font=styl.CZCIONKA_TRESC,
        text_color=kolor_tekstu,
        wraplength=420,
        justify="left",
    ).pack(padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY)
    toast.place(relx=1.0, rely=1.0, x=-styl.ODSTEP_DUZY, y=-styl.ODSTEP_DUZY, anchor="se")

    root._aktywny_toast = toast

    def _zamknij() -> None:
        if toast.winfo_exists():
            toast.destroy()
        if getattr(root, "_aktywny_toast", None) is toast:
            root._aktywny_toast = None

    toast.after(_CZAS_TOASTU_MS, _zamknij)
