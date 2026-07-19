from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Firma, KosztReczny
from app.schemas.koszt_reczny import KosztRecznyCreate, KosztRecznyUpdate


def _pobierz_jedyna_firme(db: Session) -> Firma:
    firma = db.execute(select(Firma)).scalars().first()
    if firma is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dane firmy nie sa jeszcze uzupelnione.",
        )
    return firma


def lista_kosztow(
    db: Session,
    data_od: date | None,
    data_do: date | None,
    skip: int,
    limit: int,
) -> list[KosztReczny]:
    zapytanie = select(KosztReczny)
    if data_od is not None:
        zapytanie = zapytanie.where(KosztReczny.data >= data_od)
    if data_do is not None:
        zapytanie = zapytanie.where(KosztReczny.data <= data_do)
    zapytanie = (
        zapytanie.order_by(KosztReczny.data.desc(), KosztReczny.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(zapytanie).scalars().all())


def pobierz_koszt(db: Session, koszt_id: int) -> KosztReczny:
    koszt = db.get(KosztReczny, koszt_id)
    if koszt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono kosztu recznego o podanym id.",
        )
    return koszt


def utworz_koszt(db: Session, dane: KosztRecznyCreate) -> KosztReczny:
    firma = _pobierz_jedyna_firme(db)
    koszt = KosztReczny(
        firma_id=firma.id,
        data=dane.data,
        kwota_grosze=dane.kwota_grosze,
        kategoria=dane.kategoria,
        opis=dane.opis,
    )
    db.add(koszt)
    db.commit()
    db.refresh(koszt)
    return koszt


def aktualizuj_koszt(db: Session, koszt_id: int, dane: KosztRecznyUpdate) -> KosztReczny:
    koszt = pobierz_koszt(db, koszt_id)
    zmiany = dane.model_dump(exclude_unset=True)
    for pole, wartosc in zmiany.items():
        setattr(koszt, pole, wartosc)
    db.commit()
    db.refresh(koszt)
    return koszt


def usun_koszt(db: Session, koszt_id: int) -> None:
    koszt = pobierz_koszt(db, koszt_id)
    db.delete(koszt)
    db.commit()
