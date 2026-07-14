import threading
import tkinter as tk
from typing import Callable, Protocol, TypeVar

from gui.api_client import ApiError

T = TypeVar("T")


class WskaznikLadowania(Protocol):
    """Protokol wskaznika ladowania (np. Tabela albo przycisk z tekstem
    'Zapisywanie...') - uruchom_w_tle woła te dwie metody automatycznie wokol
    zadania w tle, zeby nie trzeba bylo tego recznie powtarzac w kazdym
    wywolaniu (Faza 16C)."""

    def pokaz_ladowanie(self) -> None: ...

    def ukryj_ladowanie(self) -> None: ...


def uruchom_w_tle(
    widget: tk.Misc,
    zadanie: Callable[[], T],
    on_sukces: Callable[[T], None],
    on_blad: Callable[[ApiError], None],
    wskaznik: WskaznikLadowania | None = None,
) -> None:
    """Uruchamia `zadanie` (blokujace, np. wywolanie api_client) w osobnym watku,
    zeby nie zamrazac UI. Wynik/blad wraca na watek Tk przez `widget.after(0, ...)`,
    bo Tkinter nie jest bezpieczny watkowo.

    Sprawdzenie `widget.winfo_exists()` siedzi WEWNATRZ funkcji planowanej przez
    `.after()`, nie przed jej zaplanowaniem - inaczej mozliwy jest wyscig miedzy
    watkiem w tle a zniszczeniem widgetu (np. zamknieciem okna) w watku Tk. Samo
    zaplanowanie `.after()` jest owiniete w try/except na wypadek gdyby widget byl
    juz zniszczony w momencie planowania.

    `wskaznik` (opcjonalny) dostaje `pokaz_ladowanie()` tuz przed startem watku
    i `ukryj_ladowanie()` tuz przed dostarczeniem wyniku/bledu - w praktyce
    najczesciej `sukces()` i tak od razu nadpisuje ten sam widok swiezymi
    danymi, wiec `ukryj_ladowanie()` ma znaczenie glownie na sciezce bledu.
    """
    if wskaznik is not None:
        wskaznik.pokaz_ladowanie()

    def watek() -> None:
        try:
            wynik = zadanie()
        except ApiError as e:
            _dostarcz(widget, wskaznik, on_blad, e)
        except Exception as e:  # nieoczekiwany wyjatek - tez pokazujemy uzytkownikowi
            _dostarcz(widget, wskaznik, on_blad, ApiError(f"Nieoczekiwany błąd: {e}"))
        else:
            _dostarcz(widget, wskaznik, on_sukces, wynik)

    threading.Thread(target=watek, daemon=True).start()


def _dostarcz(
    widget: tk.Misc,
    wskaznik: WskaznikLadowania | None,
    callback: Callable[..., None],
    arg,
) -> None:
    def na_watku_glownym() -> None:
        if widget.winfo_exists():
            if wskaznik is not None:
                wskaznik.ukryj_ladowanie()
            callback(arg)

    try:
        widget.after(0, na_watku_glownym)
    except tk.TclError:
        pass  # widget juz zniszczony w momencie planowania
