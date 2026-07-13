from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura, PlatnoscFaktury
from app.models.enums import StatusFaktury
from app.schemas.faktura import FakturaOut, PlatnoscCreate
from app.services.faktury import pobierz_fakture

# Faktury w tych statusach nie maja jeszcze wystawionego zobowiazania platniczego
# (robocza) albo sa juz definitywnie zamkniete bez oczekiwania na zaplate (anulowana) -
# rejestrowanie do nich platnosci nie ma sensu biznesowego.
STATUSY_BLOKUJACE_PLATNOSC: frozenset[StatusFaktury] = frozenset(
    {StatusFaktury.ROBOCZA, StatusFaktury.ANULOWANA}
)

# Faktury, dla ktorych ma sens wyliczanie naleznosci (nie sa jeszcze w pelni
# rozliczone ani anulowane/robocze).
STATUSY_NALEZNOSCI: frozenset[StatusFaktury] = frozenset(
    {
        StatusFaktury.WYSTAWIONA,
        StatusFaktury.WYSLANA,
        StatusFaktury.OPLACONA_CZESCIOWO,
        StatusFaktury.PO_TERMINIE,
    }
)


def oblicz_status_efektywny(faktura: Faktura, dzisiaj: date) -> StatusFaktury:
    """Wylicza status faktury na podstawie sumy wplat i terminu platnosci, bez
    zapisu do bazy - uzywane zarowno do wyswietlania (GET, gdzie przejscie w
    "po terminie" nie jest trwale zapisywane), jak i do wyliczenia statusu,
    ktory FAKTYCZNIE zostanie zapisany po zarejestrowaniu platnosci (patrz
    dodaj_platnosc - tam suma wplat > 0, wiec galaz "po terminie" tam nie zadziala).
    """
    if faktura.status in (
        StatusFaktury.ROBOCZA,
        StatusFaktury.ANULOWANA,
        StatusFaktury.OPLACONA,
    ):
        return faktura.status

    suma_wplat = faktura.suma_wplat_grosze
    brutto = faktura.suma_brutto_grosze

    if suma_wplat == 0:
        if faktura.termin_platnosci < dzisiaj:
            return StatusFaktury.PO_TERMINIE
        return faktura.status

    if suma_wplat < brutto:
        return StatusFaktury.OPLACONA_CZESCIOWO

    return StatusFaktury.OPLACONA


def zbuduj_fakture_out(faktura: Faktura, dzisiaj: date | None = None) -> FakturaOut:
    # Atrybut przejsciowy (nie mapowana kolumna) - bezpieczny do ustawienia na
    # instancji ORM, SQLAlchemy nie sledzi go w unit-of-work, wiec nic nie zapisze.
    faktura.status_efektywny = oblicz_status_efektywny(faktura, dzisiaj or date.today())
    return FakturaOut.model_validate(faktura)


def pobierz_platnosci_faktury(db: Session, faktura_id: int) -> list[PlatnoscFaktury]:
    pobierz_fakture(db, faktura_id)  # 404, jesli faktura nie istnieje
    zapytanie = (
        select(PlatnoscFaktury)
        .where(PlatnoscFaktury.faktura_id == faktura_id)
        .order_by(PlatnoscFaktury.data_platnosci.desc(), PlatnoscFaktury.id.desc())
    )
    return list(db.execute(zapytanie).scalars().all())


def dodaj_platnosc(
    db: Session, faktura_id: int, dane: PlatnoscCreate
) -> PlatnoscFaktury:
    faktura = pobierz_fakture(db, faktura_id)

    if faktura.status in STATUSY_BLOKUJACE_PLATNOSC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nie mozna dodac platnosci do faktury w statusie "
                f"'{faktura.status.value}'."
            ),
        )

    pozostalo_grosze = faktura.kwota_pozostala_grosze
    if dane.kwota_grosze > pozostalo_grosze:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Kwota platnosci przekracza kwote pozostala do zaplaty "
                f"({pozostalo_grosze / 100:.2f} {faktura.waluta}). Nadplaty nie sa "
                "obslugiwane."
            ),
        )

    platnosc = PlatnoscFaktury(
        faktura_id=faktura.id,
        data_platnosci=dane.data_platnosci,
        kwota_grosze=dane.kwota_grosze,
        notatka=dane.notatka,
    )
    faktura.platnosci.append(platnosc)

    nowy_status = oblicz_status_efektywny(faktura, date.today())
    if nowy_status != faktura.status:
        faktura.status = nowy_status

    db.add(platnosc)
    db.commit()
    db.refresh(platnosc)
    return platnosc


def lista_naleznosci(
    db: Session, dzisiaj: date | None = None
) -> tuple[list[Faktura], int]:
    dzisiaj = dzisiaj or date.today()
    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje), selectinload(Faktura.platnosci))
        .where(Faktura.status.in_(STATUSY_NALEZNOSCI))
        .order_by(Faktura.termin_platnosci.asc())
    )
    faktury = list(db.execute(zapytanie).scalars().unique().all())
    suma_grosze = sum(f.kwota_pozostala_grosze for f in faktury)
    return faktury, suma_grosze
