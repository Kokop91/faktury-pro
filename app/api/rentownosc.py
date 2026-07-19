from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.rentownosc import MarzaOkresuOut, PrognozaWplywowOut, RentownoscProduktuOut
from app.services import rentownosc_service

router = APIRouter(prefix="/rentownosc", tags=["rentownosc"])


@router.get("/marza", response_model=MarzaOkresuOut)
def marza(
    rok: int = Query(..., ge=1900, le=2100),
    miesiac: int | None = Query(default=None, ge=1, le=12),
    wariant: str = Query(..., pattern="^(miesieczny|kwartalny|roczny)$"),
    db: Session = Depends(get_db),
):
    data_od, data_do = rentownosc_service.zakres_dat(rok, miesiac, wariant)
    return rentownosc_service.marza_okresu(db, data_od, data_do)


@router.get("/produkty", response_model=list[RentownoscProduktuOut])
def rentownosc_produktow(
    rok: int = Query(..., ge=1900, le=2100),
    miesiac: int | None = Query(default=None, ge=1, le=12),
    wariant: str = Query(..., pattern="^(miesieczny|kwartalny|roczny)$"),
    db: Session = Depends(get_db),
):
    data_od, data_do = rentownosc_service.zakres_dat(rok, miesiac, wariant)
    return rentownosc_service.rentownosc_produktow(db, data_od, data_do)


@router.get("/prognoza-wplywow", response_model=PrognozaWplywowOut)
def prognoza_wplywow(db: Session = Depends(get_db)):
    return rentownosc_service.prognoza_wplywow(db)
