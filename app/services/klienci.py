from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Firma, Klient
from app.schemas.klient import KlientCreate, KlientUpdate


def _pobierz_jedyna_firme(db: Session) -> Firma:
    firmy = db.execute(select(Firma)).scalars().all()
    if len(firmy) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Brak skonfigurowanej firmy (lub jest ich wiecej niz jedna) - "
                "dodaj dokladnie jeden rekord Firma przed utworzeniem klienta."
            ),
        )
    return firmy[0]


def pobierz_klienta(db: Session, klient_id: int) -> Klient:
    klient = db.get(Klient, klient_id)
    if klient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono klienta o podanym id.",
        )
    return klient


def lista_klientow(
    db: Session, skip: int, limit: int, tylko_aktywni: bool
) -> list[Klient]:
    zapytanie = select(Klient)
    if tylko_aktywni:
        zapytanie = zapytanie.where(Klient.aktywny.is_(True))
    zapytanie = zapytanie.order_by(Klient.id).offset(skip).limit(limit)
    return list(db.execute(zapytanie).scalars().all())


def utworz_klienta(db: Session, dane: KlientCreate) -> Klient:
    firma = _pobierz_jedyna_firme(db)
    klient = Klient(firma_id=firma.id, **dane.model_dump())
    db.add(klient)
    db.commit()
    db.refresh(klient)
    return klient


def aktualizuj_klienta(db: Session, klient_id: int, dane: KlientUpdate) -> Klient:
    klient = pobierz_klienta(db, klient_id)
    zmiany = dane.model_dump(exclude_unset=True)
    for pole, wartosc in zmiany.items():
        setattr(klient, pole, wartosc)
    db.commit()
    db.refresh(klient)
    return klient


def usun_klienta(db: Session, klient_id: int) -> None:
    """Soft-delete: klient moze miec powiazane faktury (historia sprzedazy),
    wiec fizyczne usuniecie zerwaloby integralnosc danych. Ustawiamy aktywny=False
    i domyslnie ukrywamy go z listy, ale rekord i jego faktury pozostaja nietkniete.
    """
    klient = pobierz_klienta(db, klient_id)
    klient.aktywny = False
    db.commit()
