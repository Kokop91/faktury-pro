from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.koszt_reczny import KosztRecznyCreate, KosztRecznyOut, KosztRecznyUpdate
from app.services import koszty_reczne_service

router = APIRouter(prefix="/koszty-reczne", tags=["koszty-reczne"])


@router.post("", response_model=KosztRecznyOut, status_code=201)
def utworz_koszt(dane: KosztRecznyCreate, db: Session = Depends(get_db)):
    return koszty_reczne_service.utworz_koszt(db, dane)


@router.get("", response_model=list[KosztRecznyOut])
def lista_kosztow(
    data_od: date | None = Query(default=None),
    data_do: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return koszty_reczne_service.lista_kosztow(db, data_od, data_do, skip, limit)


@router.get("/{koszt_id}", response_model=KosztRecznyOut)
def szczegoly_kosztu(koszt_id: int, db: Session = Depends(get_db)):
    return koszty_reczne_service.pobierz_koszt(db, koszt_id)


@router.put("/{koszt_id}", response_model=KosztRecznyOut)
def edytuj_koszt(koszt_id: int, dane: KosztRecznyUpdate, db: Session = Depends(get_db)):
    return koszty_reczne_service.aktualizuj_koszt(db, koszt_id, dane)


@router.delete("/{koszt_id}", status_code=204)
def usun_koszt(koszt_id: int, db: Session = Depends(get_db)):
    koszty_reczne_service.usun_koszt(db, koszt_id)
