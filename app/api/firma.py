from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.firma import FirmaCreate, FirmaOut, FirmaUpdate
from app.schemas.jpk import UrzadSkarbowyOut
from app.services import firma as firma_service
from app.services import jpk_service

router = APIRouter(prefix="/firma", tags=["firma"])


@router.get("", response_model=FirmaOut)
def pobierz_firme(db: Session = Depends(get_db)):
    return firma_service.pobierz_firme(db)


@router.get("/urzedy-skarbowe", response_model=list[UrzadSkarbowyOut])
def lista_urzedow_skarbowych():
    return jpk_service.lista_urzedow_skarbowych()


@router.post("", response_model=FirmaOut, status_code=201)
def utworz_firme(dane: FirmaCreate, db: Session = Depends(get_db)):
    return firma_service.utworz_firme(db, dane)


@router.put("", response_model=FirmaOut)
def edytuj_firme(dane: FirmaUpdate, db: Session = Depends(get_db)):
    return firma_service.aktualizuj_firme(db, dane)
