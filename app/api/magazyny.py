from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.magazyn import MagazynCreate, MagazynOut
from app.services import magazyn_service

router = APIRouter(prefix="/magazyny", tags=["magazyn"])


@router.post("", response_model=MagazynOut, status_code=201)
def dodaj_magazyn(dane: MagazynCreate, db: Session = Depends(get_db)):
    return magazyn_service.utworz_magazyn(db, dane)


@router.get("", response_model=list[MagazynOut])
def lista_magazynow(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    tylko_aktywne: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    return magazyn_service.lista_magazynow(db, skip, limit, tylko_aktywne)


@router.get("/{magazyn_id}", response_model=MagazynOut)
def szczegoly_magazynu(magazyn_id: int, db: Session = Depends(get_db)):
    return magazyn_service.pobierz_magazyn(db, magazyn_id)
