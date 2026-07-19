from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.magazyn import (
    ProduktCreate,
    ProduktKosztZakupuUpdate,
    ProduktOut,
    RuchMagazynowyOut,
)
from app.services import magazyn_service

router = APIRouter(prefix="/produkty", tags=["magazyn"])


@router.post("", response_model=ProduktOut, status_code=201)
def dodaj_produkt(dane: ProduktCreate, db: Session = Depends(get_db)):
    return magazyn_service.utworz_produkt(db, dane)


@router.get("", response_model=list[ProduktOut])
def lista_produktow(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    tylko_aktywne: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    return magazyn_service.lista_produktow(db, skip, limit, tylko_aktywne)


@router.get("/{produkt_id}", response_model=ProduktOut)
def szczegoly_produktu(produkt_id: int, db: Session = Depends(get_db)):
    return magazyn_service.pobierz_produkt(db, produkt_id)


@router.get("/{produkt_id}/historia-ruchow", response_model=list[RuchMagazynowyOut])
def historia_ruchow_produktu(produkt_id: int, db: Session = Depends(get_db)):
    return magazyn_service.historia_ruchow_produktu(db, produkt_id)


@router.patch("/{produkt_id}/koszt-zakupu", response_model=ProduktOut)
def ustaw_koszt_zakupu(
    produkt_id: int, dane: ProduktKosztZakupuUpdate, db: Session = Depends(get_db)
):
    return magazyn_service.ustaw_koszt_zakupu(db, produkt_id, dane.koszt_zakupu_grosze)
