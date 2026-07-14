import re
from datetime import date, timedelta
from decimal import Decimal

import requests
from fastapi import HTTPException, status

BASE_URL = "https://api.nbp.pl/api/exchangerates/rates/a"
TIMEOUT_S = 5.0
KOD_WALUTY_REGEX = re.compile(r"^[A-Za-z]{3}$")

# Zakres wstecz przy szukaniu ostatniej dostepnej tabeli przed data docelowa -
# NBP nie publikuje tabel w weekendy/swieta, ale nigdy nie ma dluzszej przerwy
# niz dlugi weekend, wiec 10 dni to bezpieczny zapas (limit NBP na zakres to 93 dni).
DNI_WSTECZ = 10


def pobierz_kurs_przed_data(waluta: str, data_wystawienia: date) -> tuple[Decimal, date]:
    """Kurs z ostatniego dnia roboczego PRZED data_wystawienia (zgodnie z
    przepisami o przeliczaniu walut obcych na fakturach). Zwraca (kurs,
    data_efektywna) - data_efektywna to dzien, z ktorego faktycznie pochodzi
    kurs (moze byc wczesniejszy niz data_wystawienia-1 dzien, jesli trafil
    weekend/swieto).
    """
    if not KOD_WALUTY_REGEX.match(waluta):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieprawidłowy kod waluty: {waluta}",
        )

    dzien_docelowy = data_wystawienia - timedelta(days=1)
    dzien_od = dzien_docelowy - timedelta(days=DNI_WSTECZ)
    url = (
        f"{BASE_URL}/{waluta.lower()}/{dzien_od.isoformat()}/"
        f"{dzien_docelowy.isoformat()}/?format=json"
    )

    try:
        odpowiedz = requests.get(url, timeout=TIMEOUT_S)
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Brak połączenia z serwisem NBP: {e}",
        ) from e

    if odpowiedz.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"NBP nie publikuje kursu waluty {waluta.upper()} "
                f"(sprawdź kod waluty) albo brak notowań w ostatnich "
                f"{DNI_WSTECZ} dniach."
            ),
        )
    if odpowiedz.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Serwis NBP zwrócił błąd ({odpowiedz.status_code}).",
        )

    dane = odpowiedz.json()
    notowania = dane.get("rates") or []
    if not notowania:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brak notowań NBP dla waluty {waluta.upper()} w ostatnich {DNI_WSTECZ} dniach.",
        )

    ostatnie = notowania[-1]
    kurs = Decimal(str(ostatnie["mid"]))
    data_efektywna = date.fromisoformat(ostatnie["effectiveDate"])
    return kurs, data_efektywna
