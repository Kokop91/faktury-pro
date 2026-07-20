"""Import klientow z pliku CSV (Faza 26) - konfiguracja kreatora wspoldzielonego
w gui/windows/dialog_importu_csv.py. Odpowiada wylacznie za: liste pol Klienta
(z aliasami do auto-dopasowania kolumn) i parsowanie surowego tekstu z pliku na
gotowe wartosci - walidacja regul biznesowych (wymagane pola, format NIP,
duplikat NIP wzgledem bazy) jest juz wykonywana przez backend (patrz
app/services/klienci.py:importuj_klientow), wywolywany tu w trybie "suchym"
do podgladu i w trybie zapisu do faktycznego importu.
"""

from typing import Callable

from gui import api_client
from gui.windows.dialog_importu_csv import DialogImportuCsv

# (klucz, etykieta, wymagane, aliasy_naglowkow_do_auto_dopasowania)
_POLA = [
    ("nazwa", "Nazwa *", True, ("nazwa", "name", "firma", "nazwa firmy", "kontrahent")),
    ("nip", "NIP", False, ("nip", "tax id", "vat id", "nip firmy")),
    ("ulica", "Ulica", False, ("ulica", "adres", "address", "street")),
    ("kod_pocztowy", "Kod pocztowy", False, ("kod pocztowy", "kod", "zip", "postal code")),
    ("miejscowosc", "Miejscowość", False, ("miejscowosc", "miasto", "city")),
    ("kraj", "Kraj", False, ("kraj", "country")),
    ("email", "Email", False, ("email", "e-mail", "mail")),
    ("telefon", "Telefon", False, ("telefon", "tel", "phone", "numer telefonu")),
    ("domyslna_waluta", "Domyślna waluta", False, ("waluta", "currency")),
    (
        "domyslny_termin_platnosci_dni",
        "Termin płatności (dni)",
        False,
        ("termin platnosci", "termin platnosci dni", "payment terms", "termin"),
    ),
]

_POLA_TEKSTOWE = ("ulica", "kod_pocztowy", "miejscowosc", "kraj", "email", "telefon", "domyslna_waluta")


class DialogImportuKlientow(DialogImportuCsv):
    KOLUMNY_PODGLADU = ["nazwa", "nip", "miejscowosc"]

    def __init__(self, master, on_zaimportowano: Callable[[], None]):
        super().__init__(master, "Importuj klientów z CSV", on_zaimportowano)

    def pola(self):
        return _POLA

    def koerencja_wiersza(self, surowe: dict[str, str]) -> tuple[dict | None, str | None]:
        nazwa = surowe.get("nazwa", "").strip()
        if not nazwa:
            return None, "brak nazwy (pole wymagane)"

        dane: dict = {"nazwa": nazwa}

        nip_tekst = surowe.get("nip", "").strip()
        if nip_tekst:
            dane["nip"] = "".join(znak for znak in nip_tekst if znak.isdigit())

        for klucz in _POLA_TEKSTOWE:
            wartosc = surowe.get(klucz, "").strip()
            if wartosc:
                dane[klucz] = wartosc

        termin_tekst = surowe.get("domyslny_termin_platnosci_dni", "").strip()
        if termin_tekst:
            try:
                dane["domyslny_termin_platnosci_dni"] = int(termin_tekst)
            except ValueError:
                return None, f"nieprawidłowy termin płatności „{termin_tekst}” (musi być liczbą całkowitą dni)"

        return dane, None

    def wywolaj_podglad(self, wiersze: list[dict]) -> list[dict]:
        return api_client.podglad_importu_klientow(wiersze)

    def wywolaj_import(self, wiersze: list[dict]) -> list[dict]:
        return api_client.importuj_klientow(wiersze)
