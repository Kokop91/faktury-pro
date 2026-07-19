"""Ikony rysowane programowo przez PIL (Faza 16A) - CELOWO bez plikow zasobow
(.png/.svg) ani biblioteki ikon pobieranej z internetu: appka ma dzialac w
100% offline, a PIL jest juz zaleznoscia projektu (requirements.txt, potrzebny
tez przez customtkinter.CTkImage). Kazdy ksztalt jest rysowany w siatce 24x24,
renderowany w wyzszej rozdzielczosci i skalowany w dol (LANCZOS) dla gladkich
krawedzi nawet na ekranach HighDPI.

Dwa warianty koloru:
- ikona_stala(...)   - staly jasny kolor, do uzycia na powierzchniach ktore
  NIE zmieniaja sie z trybem jasny/ciemny (pasek boczny, przyciski akcentowe).
- ikona_adaptacyjna(...) - kolor podazajacy za trybem wygladu (jak
  text_color=styl.KOLOR_TEKST_GLOWNY), do przyciskow drugorzednych stojacych
  na tle karty/strony.
"""

import math
from typing import Callable

import customtkinter as ctk
from PIL import Image, ImageDraw

from gui import styl

_SIATKA = 24
_SUPERSAMPLING = 4

_cache: dict[tuple, ctk.CTkImage] = {}


def _rysuj_dokument(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    rysuj.rounded_rectangle(
        [s(5), s(3), s(19), s(21)], radius=s(2), outline="white", width=w
    )
    for y in (9, 13, 17):
        rysuj.line([s(8), s(y), s(16), s(y)], fill="white", width=w)


def _rysuj_wallet(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    rysuj.rounded_rectangle(
        [s(4), s(7), s(20), s(18)], radius=s(2.5), outline="white", width=w
    )
    rysuj.ellipse([s(15), s(11), s(18.5), s(14.5)], outline="white", width=w)


def _rysuj_osoba(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    rysuj.ellipse([s(8.6), s(4.2), s(15.4), s(11)], outline="white", width=w)
    rysuj.polygon(
        [(s(7), s(21)), (s(17), s(21)), (s(18.5), s(13.5)), (s(5.5), s(13.5))],
        outline="white",
        width=w,
    )


def _rysuj_magazyn(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    rysuj.rectangle([s(4.5), s(10), s(19.5), s(20)], outline="white", width=w)
    rysuj.line([s(4.5), s(10), s(12), s(4.5)], fill="white", width=w)
    rysuj.line([s(12), s(4.5), s(19.5), s(10)], fill="white", width=w)
    rysuj.line([s(12), s(4.5), s(12), s(10)], fill="white", width=w)


def _rysuj_zebatka(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    cx, cy = s(12), s(12)
    rysuj.ellipse(
        [s(12 - 3.6), s(12 - 3.6), s(12 + 3.6), s(12 + 3.6)], outline="white", width=w
    )
    for i in range(8):
        kat = math.radians(i * 45)
        x1 = cx + s(5.4) * math.cos(kat)
        y1 = cy + s(5.4) * math.sin(kat)
        x2 = cx + s(7.6) * math.cos(kat)
        y2 = cy + s(7.6) * math.sin(kat)
        rysuj.line([x1, y1, x2, y2], fill="white", width=w)


def _rysuj_plus(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    rysuj.line([s(12), s(5), s(12), s(19)], fill="white", width=w)
    rysuj.line([s(5), s(12), s(19), s(12)], fill="white", width=w)


def _rysuj_dashboard(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    rysuj.rectangle([s(4.5), s(13), s(9), s(20)], outline="white", width=w)
    rysuj.rectangle([s(10.25), s(8), s(14.75), s(20)], outline="white", width=w)
    rysuj.rectangle([s(16), s(4), s(20.5), s(20)], outline="white", width=w)


def _rysuj_wplyw(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    """Tacka (skrzynka odbiorcza) ze strzalka skierowana w dol - symbolizuje
    dokumenty PRZYCHODZACE (faktury kosztowe odebrane z KSeF), w odroznieniu
    od ikony "faktury" (wystawiane, wychodzace)."""
    rysuj.line([s(4.5), s(14), s(4.5), s(20)], fill="white", width=w)
    rysuj.line([s(4.5), s(20), s(19.5), s(20)], fill="white", width=w)
    rysuj.line([s(19.5), s(20), s(19.5), s(14)], fill="white", width=w)
    rysuj.line([s(12), s(3.5), s(12), s(14.5)], fill="white", width=w)
    rysuj.polygon([(s(8), s(11)), (s(16), s(11)), (s(12), s(15.5))], fill="white")


def _rysuj_oferta(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    """Dokument (jak _rysuj_dokument) z ptaszkiem zamiast linii tekstu -
    symbolizuje oferte/wycene oczekujaca na akceptacje klienta, w odroznieniu
    od ikony "faktury" (juz wystawiony dokument ksiegowy)."""
    rysuj.rounded_rectangle(
        [s(5), s(3), s(19), s(21)], radius=s(2), outline="white", width=w
    )
    rysuj.line([s(8.5), s(13), s(11), s(15.5)], fill="white", width=w)
    rysuj.line([s(11), s(15.5), s(15.5), s(9.5)], fill="white", width=w)


def _rysuj_rentownosc(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    """Linia trendu rosnacego ze strzalka - symbolizuje analize rentownosci/
    marzy (Faza 25), w odroznieniu od slupkowej ikony "dashboard"."""
    rysuj.line(
        [(s(4.5), s(18)), (s(9.5), s(12)), (s(13.5), s(15)), (s(19.5), s(6))],
        fill="white",
        width=w,
        joint="curve",
    )
    rysuj.polygon(
        [(s(19.5), s(6)), (s(14.5), s(6.5)), (s(19), s(10.5))],
        fill="white",
    )


def _rysuj_cykl(rysuj: ImageDraw.ImageDraw, s: Callable[[float], float], w: float) -> None:
    """Dwa luki z grocikami (jak ikona "odswiez/powtorz") - symbolizuja
    powtarzajacy sie w czasie szablon faktury cyklicznej."""
    bbox = [s(4.5), s(4.5), s(19.5), s(19.5)]
    rysuj.arc(bbox, start=200, end=340, fill="white", width=w)
    rysuj.arc(bbox, start=20, end=160, fill="white", width=w)
    rysuj.polygon([(s(19.4), s(9.6)), (s(16.2), s(7.6)), (s(17.6), s(11.6))], fill="white")
    rysuj.polygon([(s(4.6), s(14.4)), (s(7.8), s(16.4)), (s(6.4), s(12.4))], fill="white")


_RYSOWNICE: dict[str, Callable[[ImageDraw.ImageDraw, Callable[[float], float], int], None]] = {
    "faktury": _rysuj_dokument,
    "oferty": _rysuj_oferta,
    "naleznosci": _rysuj_wallet,
    "klienci": _rysuj_osoba,
    "magazyn": _rysuj_magazyn,
    "ustawienia": _rysuj_zebatka,
    "plus": _rysuj_plus,
    "dashboard": _rysuj_dashboard,
    "cykliczne": _rysuj_cykl,
    "koszty": _rysuj_wplyw,
    "rentownosc": _rysuj_rentownosc,
}


def _obraz(nazwa: str, kolor: str, rozmiar: int) -> Image.Image:
    render_px = rozmiar * _SUPERSAMPLING
    skala = render_px / _SIATKA

    def s(wartosc: float) -> float:
        return wartosc * skala

    obraz = Image.new("RGBA", (render_px, render_px), (0, 0, 0, 0))
    rysuj = ImageDraw.Draw(obraz)
    grubosc = max(1, round(skala * 1.6))
    _RYSOWNICE[nazwa](rysuj, s, grubosc)

    if kolor != "white":
        # Wszystkie ksztalty rysowane sa na "white" - tutaj podmieniamy na docelowy
        # kolor przez maske alfa, zeby _RYSOWNICE nie musialy znac koloru docelowego.
        maska = obraz.split()[3]
        wynik = Image.new("RGBA", obraz.size, kolor)
        wynik.putalpha(maska)
        obraz = wynik

    return obraz.resize((rozmiar, rozmiar), Image.LANCZOS)


def ikona_stala(nazwa: str, rozmiar: int = 18) -> ctk.CTkImage:
    """Ikona o stalym jasnym kolorze (styl.KOLOR_IKONY_NA_STALE_CIEMNYM) - do
    przyciskow/pozycji na powierzchniach ktore sa ciemne w obu trybach wygladu
    (pasek boczny, przyciski akcentowe)."""
    klucz = ("stala", nazwa, rozmiar)
    if klucz not in _cache:
        obraz = _obraz(nazwa, styl.KOLOR_IKONY_NA_STALE_CIEMNYM, rozmiar)
        _cache[klucz] = ctk.CTkImage(light_image=obraz, dark_image=obraz, size=(rozmiar, rozmiar))
    return _cache[klucz]


def ikona_adaptacyjna(nazwa: str, rozmiar: int = 16) -> ctk.CTkImage:
    """Ikona zmieniajaca kolor razem z trybem wygladu (analogicznie do
    text_color=styl.KOLOR_TEKST_GLOWNY) - do przyciskow drugorzednych (obrys)
    stojacych na tle karty/strony, ktore SA rozne w trybie jasnym/ciemnym."""
    klucz = ("adaptacyjna", nazwa, rozmiar)
    if klucz not in _cache:
        jasny = _obraz(nazwa, styl.KOLOR_IKONY_JASNY_TRYB, rozmiar)
        ciemny = _obraz(nazwa, styl.KOLOR_IKONY_CIEMNY_TRYB, rozmiar)
        _cache[klucz] = ctk.CTkImage(light_image=jasny, dark_image=ciemny, size=(rozmiar, rozmiar))
    return _cache[klucz]
