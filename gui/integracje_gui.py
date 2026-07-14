import re
from typing import Callable

import customtkinter as ctk

from gui import api_client, formatowanie, styl
from gui.api_client import ApiError
from gui.watki import uruchom_w_tle
from gui.widgets_pomocnicze import Banner, pokaz_toast, ustaw_tekst_ladowania

NIP_REGEX = re.compile(r"^\d{10}$")


def pobierz_z_gus(
    widget: ctk.CTkBaseClass,
    nip: str,
    przycisk: ctk.CTkButton,
    banner: Banner,
    wypelnij: Callable[[dict], None],
) -> None:
    """Wspolna logika przycisku "Pobierz z GUS" - uzywana z formularza klienta
    i z ustawien firmy. `wypelnij` dostaje slownik {nazwa, ulica, kod_pocztowy,
    miejscowosc} i ma za zadanie wstawic te wartosci do wlasciwych pol
    wywolujacego formularza."""
    nip = nip.strip()
    if not NIP_REGEX.match(nip):
        banner.pokaz("Podaj poprawny NIP (10 cyfr), żeby pobrać dane z GUS.")
        return
    banner.ukryj()

    ustaw_tekst_ladowania(przycisk, True, "Pobierz z GUS", "Pobieranie z GUS...")

    def zadanie():
        return api_client.szukaj_w_gus(nip)

    def sukces(podmiot: dict) -> None:
        ustaw_tekst_ladowania(przycisk, False, "Pobierz z GUS")
        wypelnij(podmiot)
        pokaz_toast(widget, f"Pobrano dane z GUS: {podmiot.get('nazwa') or nip}.")

    def blad(e: ApiError) -> None:
        ustaw_tekst_ladowania(przycisk, False, "Pobierz z GUS")
        if e.status_code == 404:
            banner.pokaz(f"Nie znaleziono podmiotu o NIP {nip} w rejestrze REGON.")
        elif e.status_code == 400:
            banner.pokaz(e.komunikat)
        else:
            banner.pokaz("Brak połączenia z GUS — wpisz dane ręcznie.")

    uruchom_w_tle(widget, zadanie, sukces, blad)


def _opisz_wynik_bialej_listy(wynik: dict) -> tuple[str, tuple]:
    """Zwraca (tekst, kolor_krotka_jasny_ciemny) do wyswietlenia."""
    znacznik_czasu = formatowanie.formatuj_data_czas(wynik["sprawdzono_o"])

    if not wynik["znaleziono"]:
        return (
            f"Nie znaleziono w wykazie podatników VAT (sprawdzono {znacznik_czasu}).",
            styl.KOLOR_BLAD,
        )

    status_vat = wynik.get("status_vat") or "brak statusu VAT"
    tekst = f"Status VAT: {status_vat}"
    kolor = styl.KOLOR_SUKCES if status_vat == "Czynny" else styl.KOLOR_OSTRZEZENIE

    if wynik.get("numer_konta"):
        if wynik.get("konto_zgodne"):
            tekst += " · numer konta zgodny z wykazem"
        else:
            tekst += " · NUMER KONTA NIEZGODNY Z WYKAZEM"
            kolor = styl.KOLOR_BLAD

    tekst += f" (sprawdzono {znacznik_czasu})"
    return tekst, kolor


def sprawdz_biala_liste(
    widget: ctk.CTkBaseClass,
    nip: str,
    przycisk: ctk.CTkButton,
    etykieta_wyniku: ctk.CTkLabel,
    numer_konta: str | None = None,
    klient_id: int | None = None,
    faktura_id: int | None = None,
    po_zapisaniu: Callable[[dict], None] | None = None,
) -> None:
    """Wspolna logika przycisku "Sprawdź w białej liście" - uzywana przy
    kliencie (sam NIP) i przy fakturze (NIP + numer konta wlasnej firmy).
    Wynik jest jednoczesnie zapisywany po stronie backendu jako nowy wpis
    historii (patrz app/services/biala_lista_service.py), wiec kazde klikniecie
    to nowy, trwaly dowod sprawdzenia - nie nadpisuje poprzedniego."""
    nip = nip.strip()
    if not NIP_REGEX.match(nip):
        etykieta_wyniku.configure(
            text="Podaj poprawny NIP (10 cyfr), żeby sprawdzić w białej liście.",
            text_color=styl.KOLOR_BLAD,
        )
        return

    ustaw_tekst_ladowania(przycisk, True, "Sprawdź w białej liście", "Sprawdzanie...")

    def zadanie():
        return api_client.sprawdz_biala_liste(
            nip, numer_konta=numer_konta, klient_id=klient_id, faktura_id=faktura_id
        )

    def sukces(wynik: dict) -> None:
        ustaw_tekst_ladowania(przycisk, False, "Sprawdź w białej liście")
        tekst, kolor = _opisz_wynik_bialej_listy(wynik)
        etykieta_wyniku.configure(text=tekst, text_color=kolor)
        if po_zapisaniu:
            po_zapisaniu(wynik)

    def blad(e: ApiError) -> None:
        ustaw_tekst_ladowania(przycisk, False, "Sprawdź w białej liście")
        if e.status_code == 400:
            etykieta_wyniku.configure(text=e.komunikat, text_color=styl.KOLOR_BLAD)
        else:
            etykieta_wyniku.configure(
                text="Brak połączenia z wykazem VAT — spróbuj ponownie później.",
                text_color=styl.KOLOR_OSTRZEZENIE,
            )

    uruchom_w_tle(widget, zadanie, sukces, blad)
