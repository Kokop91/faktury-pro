from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Firma
from app.schemas.firma import FirmaCreate, FirmaUpdate


def pobierz_firme(db: Session) -> Firma:
    firmy = db.execute(select(Firma)).scalars().all()
    if len(firmy) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dane firmy nie zostały jeszcze skonfigurowane.",
        )
    if len(firmy) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="W bazie jest więcej niż jeden rekord Firma - wymaga ręcznej korekty.",
        )
    return firmy[0]


def utworz_firme(db: Session, dane: FirmaCreate) -> Firma:
    if db.execute(select(Firma)).scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dane firmy są już skonfigurowane - użyj edycji zamiast tworzenia od nowa.",
        )
    firma = Firma(**dane.model_dump())
    db.add(firma)
    db.commit()
    db.refresh(firma)
    return firma


def aktualizuj_firme(db: Session, dane: FirmaUpdate) -> Firma:
    firma = pobierz_firme(db)
    zmiany = dane.model_dump(exclude_unset=True)
    for pole, wartosc in zmiany.items():
        setattr(firma, pole, wartosc)
    db.commit()
    db.refresh(firma)
    return firma
