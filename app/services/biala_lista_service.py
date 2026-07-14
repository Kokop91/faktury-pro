import re
from datetime import date

import requests
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WeryfikacjaBialejListy

BASE_URL = "https://wl-api.mf.gov.pl/api"
TIMEOUT_S = 8.0
NIP_REGEX = re.compile(r"^\d{10}$")


def _wykonaj_zapytanie(sciezka: str) -> dict:
    try:
        odpowiedz = requests.get(f"{BASE_URL}{sciezka}", timeout=TIMEOUT_S)
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Brak połączenia z wykazem podatników VAT (MF): {e}",
        ) from e

    if odpowiedz.status_code == 400:
        try:
            komunikat = odpowiedz.json().get("message", "Nieprawidłowe zapytanie.")
        except ValueError:
            komunikat = "Nieprawidłowe zapytanie."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=komunikat)
    if odpowiedz.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Wykaz podatników VAT zwrócił błąd ({odpowiedz.status_code}).",
        )
    return odpowiedz.json()


def sprawdz_nip(
    db: Session,
    nip: str,
    numer_konta: str | None = None,
    klient_id: int | None = None,
    faktura_id: int | None = None,
    data_na_dzien: date | None = None,
) -> WeryfikacjaBialejListy:
    """Sprawdza NIP w wykazie (metoda 'search'); jesli podano numer_konta,
    dodatkowo woła metode 'check' zgodnosci rachunku. Kazde wywolanie zapisuje
    NOWY wpis w historii (nigdy nie nadpisuje poprzedniego) - to celowe, wynik
    ma znaczenie dowodowe przy kontroli skarbowej."""
    if not NIP_REGEX.match(nip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NIP musi się składać z dokładnie 10 cyfr.",
        )

    data_na_dzien = data_na_dzien or date.today()

    wynik = _wykonaj_zapytanie(f"/search/nip/{nip}?date={data_na_dzien.isoformat()}")
    podmiot = (wynik.get("result") or {}).get("subject")

    konto_zgodne = None
    if podmiot is not None and numer_konta:
        numer_oczyszczony = re.sub(r"\s+", "", numer_konta)
        wynik_konta = _wykonaj_zapytanie(
            f"/check/nip/{nip}/bank-account/{numer_oczyszczony}"
            f"?date={data_na_dzien.isoformat()}"
        )
        konto_zgodne = (wynik_konta.get("result") or {}).get("accountAssigned") == "TAK"

    wpis = WeryfikacjaBialejListy(
        klient_id=klient_id,
        faktura_id=faktura_id,
        nip=nip,
        numer_konta=numer_konta,
        data_na_dzien=data_na_dzien,
        znaleziono=podmiot is not None,
        status_vat=podmiot.get("statusVat") if podmiot else None,
        nazwa_podmiotu=podmiot.get("name") if podmiot else None,
        konto_zgodne=konto_zgodne,
    )
    db.add(wpis)
    db.commit()
    db.refresh(wpis)
    return wpis


def historia_klienta(db: Session, klient_id: int) -> list[WeryfikacjaBialejListy]:
    zapytanie = (
        select(WeryfikacjaBialejListy)
        .where(WeryfikacjaBialejListy.klient_id == klient_id)
        .order_by(WeryfikacjaBialejListy.sprawdzono_o.desc())
    )
    return list(db.execute(zapytanie).scalars().all())


def historia_faktury(db: Session, faktura_id: int) -> list[WeryfikacjaBialejListy]:
    zapytanie = (
        select(WeryfikacjaBialejListy)
        .where(WeryfikacjaBialejListy.faktura_id == faktura_id)
        .order_by(WeryfikacjaBialejListy.sprawdzono_o.desc())
    )
    return list(db.execute(zapytanie).scalars().all())
